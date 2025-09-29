import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import DriverParams

import aiohttp


from pipecat.transports.daily.utils import (
    DailyMeetingTokenParams,
    DailyMeetingTokenProperties,
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
)

from app.core.config import DAILY_API_KEY, DAILY_API_URL, MAX_SESSION_TIME


from loguru import logger



bot_procs = {}


daily_rest = DailyRESTHelper(daily_api_key=DAILY_API_KEY, daily_api_url=DAILY_API_URL,aiohttp_session=aiohttp.ClientSession())


# Create the FastAPI app instance
app = FastAPI(title="NY Voice API", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/driver/voice/connect")
async def driver_voice_connect(request: DriverParams):
    logger.info(f"Driver connected params: {request}")

    driver_number = request.phoneNumber


    daily_room_properties = DailyRoomProperties(
        exp=time.time() + MAX_SESSION_TIME,
        eject_at_room_exp=True,
    )

    room = await daily_rest.create_room(
        params=DailyRoomParams(properties=daily_room_properties)
    )

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
    room.url,
    "-t",
    token,
    "--session-id",
    session_id,
    ]

    if driver_number:
        cmd += ["--driver-number", driver_number]

    logger.info(f"Starting voice agent with command: {cmd}")

    proc = subprocess.Popen(
        cmd,
        cwd=Path(__file__).parent.parent,
        bufsize=1,
    )

    bot_procs[proc.pid] = (proc, room.url)

    logger.info(f"Voice agent started with PID: {proc.pid}")
    
    return {"room_url": room.url, "token": token}


@app.get("/")
async def root():
    return {"message": "Welcome to NY Voice API"}

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
