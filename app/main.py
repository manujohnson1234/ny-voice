import os
import subprocess
import time
import uuid
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import DriverParams, LanguageCode

import aiohttp


from pipecat.transports.daily.utils import (
    DailyMeetingTokenParams,
    DailyMeetingTokenProperties,
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
)

from app.core.config import (
    DAILY_API_KEY,
    DAILY_API_URL,
    MAX_SESSION_TIME,
    NOTIFY_ENDPOINT,
    ROUTER_URL,
    POD_NAME,
    POD_IP,
    PORT,
)


from loguru import logger



bot_procs = {}


def _pod_endpoint() -> str | None:
    """Return the stable endpoint that other services should call."""
    if NOTIFY_ENDPOINT:
        return NOTIFY_ENDPOINT
    if POD_IP:
        return f"http://{POD_IP}:{PORT}"
    return None

daily_rest = None

if os.getenv("ENVIRONMENT") == "dev":
    daily_rest = DailyRESTHelper(daily_api_key=DAILY_API_KEY, daily_api_url=DAILY_API_URL, aiohttp_session=aiohttp.ClientSession())


# Create the FastAPI app instance
app = FastAPI(title="NY Voice API", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/start-session")
async def driver_voice_connect(request: DriverParams): # use this for dev env
# async def driver_voice_connect():
    # Get values from environment variables

    language_code = None
    room_url = None
    token = None
    agent_name = None


    if os.getenv("ENVIRONMENT") == "dev":
        language_code = request.language_code
    else:
        language_code = os.environ.get("LANGUAGE")
        room_url = os.environ.get("ROOM_URL")
        token = os.environ.get("TOKEN")
        agent_name = os.environ.get("AGENT_NAME", "router")


    logger.info(f"Driver connected params: language={language_code}, agent={agent_name}")

    # Create room and token if not provided (or if not in dev mode)
    if os.getenv("ENVIRONMENT") == "dev":
        daily_room_properties = DailyRoomProperties(
            exp=int(time.time() + MAX_SESSION_TIME),
            eject_at_room_exp=True,
        )

        room = await daily_rest.create_room(
            params=DailyRoomParams(properties=daily_room_properties)
        )

        room_url = room.url

        token_params = DailyMeetingTokenParams(
            properties=DailyMeetingTokenProperties(
                eject_after_elapsed=MAX_SESSION_TIME,
            )
        )

        token = await daily_rest.get_token(
            room.url,
            expiry_time=MAX_SESSION_TIME,
            eject_at_token_exp=True,
            owner=True,
            params=token_params,
        )

    session_id = str(uuid.uuid4()) 

    logger.info(f"Generated session ID for new voice agent: {session_id}")

    bot_file = "app/agents/voice/driver/bot.py"

    cmd = [
    "python3",
    bot_file,
    "-u",
    room_url,
    "-t",
    token,
    "--session-id",
    session_id,
    ]


    if language_code:
        cmd += ["--language-code", language_code]
    else:
        cmd += ["--language-code", "kn"]
    
    if agent_name:
        cmd += ["--agent-name", agent_name]
    else:
        cmd += ["--agent-name", "router"]
        

    logger.info(f"Starting voice agent with command: {cmd}")

    proc = subprocess.Popen(
        cmd,
        cwd=Path(__file__).parent.parent,
        bufsize=1,
    )

    bot_procs[proc.pid] = (proc, room_url)

    logger.info(f"Voice agent started with PID: {proc.pid}")

    if os.getenv("ENVIRONMENT") == "dev":
        return {"room_url": room_url, "token": token}
    else:
        return {"status": "success"}


async def register_with_router():
    endpoint = _pod_endpoint()
    if not endpoint or not POD_NAME:
        logger.warning(f"[POD] Cannot register: endpoint={endpoint}, POD_NAME={POD_NAME}")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{ROUTER_URL}/register"
            logger.info(f"[POD] Registering with endpoint {endpoint}")
            async with session.post(url, json={
                "pod_name": POD_NAME,
                "endpoint": endpoint,
                "room_url": os.environ.get("ROOM_URL"),
                "token": os.environ.get("TOKEN")
            }) as response:
                if response.status == 200:
                    logger.info(f"[POD] Successfully registered with router")
                else:
                    logger.error(f"[POD] Registration failed with status {response.status}")
    except Exception as e:
        logger.error(f"[POD] Failed to register with router: {e}")


async def notify_session_ended():
    """Notify the router that a session has ended."""
    endpoint = _pod_endpoint()
    if not endpoint or not POD_NAME or not ROUTER_URL:
        logger.warning(f"[POD] Cannot notify session ended: endpoint={endpoint}, POD_NAME={POD_NAME}, ROUTER_URL={ROUTER_URL}")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{ROUTER_URL}/session-ended"
            logger.info(f"[POD] Notifying session ended for pod: {POD_NAME}")
            async with session.post(url, json={
                "pod_name": POD_NAME,
                "endpoint": endpoint
            }) as response:
                if response.status == 200:
                    logger.info(f"[POD] Successfully notified session ended")
                else:
                    logger.error(f"[POD] Failed to notify session ended with status {response.status}")
    except Exception as e:
        logger.error(f"[POD] Failed to notify session ended: {e}")


async def monitor_processes():
    """Background task to monitor subprocesses and notify when they terminate."""
    while True:
        try:
            dead_pids = []
            for pid, (proc, room_url) in list(bot_procs.items()):
                # Check if process has terminated
                returncode = proc.poll()
                if returncode is not None:
                    # Process has terminated
                    logger.info(f"Process {pid} terminated with return code {returncode} (room: {room_url})")
                    dead_pids.append(pid)
            
            # Clean up dead processes and notify
            if dead_pids:
                for pid in dead_pids:
                    bot_procs.pop(pid, None)
                
                # Notify router that session ended (only once, not per process)
                if POD_NAME:
                    await notify_session_ended()
            
            # Check every 10 seconds
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error monitoring processes: {e}")
            await asyncio.sleep(10)



@app.get("/")
async def root():
    return {"message": "Welcome to NY Voice API"}

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})


@app.on_event("startup")
async def startup_event():
    if os.getenv("ENVIRONMENT") != "dev":
        await driver_voice_connect()
        await register_with_router()
        asyncio.create_task(monitor_processes())
        logger.info("Started subprocess monitoring task")
    else:
        logger.info("Not in production environment, skipping registration with router")
    
    