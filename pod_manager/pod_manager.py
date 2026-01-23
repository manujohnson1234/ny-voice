import json
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from pydantic import BaseModel
import redis
import httpx
import threading
import aiohttp
from loguru import logger

import configs
from kafka_logger import KafkaLogProducer


from pipecat.transports.daily.utils import (
    DailyMeetingTokenParams,
    DailyMeetingTokenProperties,
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
)

REDIS_KEY_WARM_PODS = configs.REDIS_KEY_WARM_PODS
REDIS_KEY_ACTIVE_PODS = configs.REDIS_KEY_ACTIVE_PODS
NAMESPACE = configs.NAMESPACE
IMAGE = configs.IMAGE
MIN_IDLE = configs.MIN_IDLE
POD_CPU = configs.POD_CPU_MASTER if configs.ENVIRONMENT == "master" else configs.POD_CPU_PROD
POD_MEM = configs.POD_MEM_MASTER if configs.ENVIRONMENT == "master" else configs.POD_MEM_PROD
MAX_POD = configs.MAX_POD
REDIS_HOST = configs.REDIS_HOST
REDIS_PORT = configs.REDIS_PORT

# Initialize Kafka log producer and add as loguru sink
kafka_producer = KafkaLogProducer(bootstrap_servers=configs.KAFKA_BOOTSTRAP_SERVERS)
logger.add(kafka_producer.sink, level="INFO")

if configs.ENVIRONMENT == "prod":
    redis_client = redis.RedisCluster(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        skip_full_coverage_check=True,  # Required for AWS ElastiCache
        health_check_interval=30
    )
else:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )


try:
    config.load_incluster_config()
except Exception:
    config.load_kube_config()
k8s = client.CoreV1Api()


app = FastAPI(title="NY Voice Pod Manager")


daily_rest = DailyRESTHelper(daily_api_key=configs.DAILY_API_KEY, daily_api_url=configs.DAILY_API_URL,aiohttp_session=aiohttp.ClientSession())


class DriverParams(BaseModel):
    phoneNumber: str
    language_code: Optional[str] = None
    current_version_of_app: Optional[str] = None
    latest_version_of_app: Optional[str] = None
    ride_id: Optional[str] = None
    agent_name: Optional[str] = None


class RegisterReq(BaseModel):
    pod_name: str
    endpoint: str
    room_url: Optional[str] = None
    token: Optional[str] = None

class EndReq(BaseModel):
    pod_name: str
    endpoint: str



def async_thread(fn):
    """Runs a function in a separate thread non-blocking."""
    t = threading.Thread(target=fn, daemon=True)
    t.start()

def async_thread_async(coro):
    """Runs an async function in a separate thread non-blocking."""
    import asyncio
    def run_async():
        asyncio.run(coro)
    t = threading.Thread(target=run_async, daemon=True)
    t.start()


async def create_pod_with_room_token(language: str):
    """Create room and token, then create pod."""
    try:
        # Create a new aiohttp session within this async context
        # This ensures it's bound to the correct event loop created by asyncio.run()
        async with aiohttp.ClientSession() as session:
            # Create a new DailyRESTHelper instance with the session for this call
            daily_rest_instance = DailyRESTHelper(
                daily_api_key=configs.DAILY_API_KEY,
                daily_api_url=configs.DAILY_API_URL,
                aiohttp_session=session
            )
            
            daily_room_properties = DailyRoomProperties(
                exp=int(time.time() + configs.MAX_SESSION_TIME),
                eject_at_room_exp=True,
            )
            room = await daily_rest_instance.create_room(
                params=DailyRoomParams(properties=daily_room_properties)
            )
            token_params = DailyMeetingTokenParams(
                properties=DailyMeetingTokenProperties(
                    eject_after_elapsed=configs.MAX_SESSION_TIME,
                )
            )

            token = await daily_rest_instance.get_token(
                room.url,
                expiry_time=configs.MAX_SESSION_TIME,
                eject_at_token_exp=True,
                owner=True,
                params=token_params,
            )
            
            # Create pod with room_url and token
            create_pod(language=language, room_url=room.url, token=token)
    except Exception as e:
        logger.error(f"Error creating pod with room/token for language {language}: {e}")


def ensure_idle_pool():
    """Ensures always 3 warm pods."""
    try:
        # Test Redis connection first
        redis_client.ping()
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(f"Redis not available, skipping warm pool check: {e}")
        return
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        return
    
    try:
        # Define languages to check
        languages = ["ta", "hi", "kn", "ml", "en"]
        
        for language in languages:
            redis_key = f"{REDIS_KEY_WARM_PODS}-{language}"
            idle_count = redis_client.llen(redis_key)
            
            if idle_count < MIN_IDLE:
                to_create = MIN_IDLE - idle_count
                if to_create > 0:
                    logger.debug(f"Ensuring warm pool for {language}: {idle_count} idle, creating {to_create} pods")
                    for _ in range(to_create):
                        # Use async function to create room/token and then create pod
                        async_thread_async(create_pod_with_room_token(language))
                else:
                    logger.debug(f"Warm pool sufficient for {language}: {idle_count} idle pods")



        # if total_pods >= MAX_POD:
        #     logger.info(f"Max pods reached: {total_pods} active pods")
        #     return

        # to_create = MIN_IDLE - idle_count

        # if to_create > 0:
        #     logger.debug(f"Ensuring warm pool: {idle_count} idle, creating {to_create} pods")
        #     for _ in range(to_create):
        #         async_thread(create_pod)
        # else:
        #     logger.debug(f"Warm pool sufficient: {idle_count} idle pods")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(f"Redis connection issue during pool check: {e}")
    except Exception as e:
        logger.error(f"Error ensuring idle pool: {e}")

def delete_pod(name: str, active_entry: str):
    try:
        k8s.delete_namespaced_pod(
            name=name,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions()
        )
        try:
            redis_client.lrem(REDIS_KEY_ACTIVE_PODS, 0, active_entry)
            logger.bind(sessionId=name).info(f"Removed from active pods: {name}")
        except Exception as e:
            logger.bind(sessionId=name).error(f"Redis error when deleting pod: {e}")
        logger.bind(sessionId=name).info(f"Pod deleted: {name}")
    except Exception as e:
        logger.bind(sessionId=name).error(f"Pod delete error: {e}")




def create_pod(language: str, room_url: str, token: str):
    """Create a pod (raw pod) asynchronously."""
    try:
        pod_id = redis_client.incr("ny-voice-next-pod")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error(f"Redis connection error when creating pod: {e}")
        # Use a fallback ID based on timestamp if Redis is unavailable
        pod_id = int(time.time() * 1000) % 1000000
        logger.warning(f"Using fallback pod ID: {pod_id}")
    except Exception as e:
        logger.error(f"Redis error when creating pod: {e}")
        pod_id = int(time.time() * 1000) % 1000000
    
    name = f"pipecat-agent-{pod_id}-{language}"

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=name,
            labels={"app": "pipecat-agent"}
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            **({"node_selector": {
                "node-type": "generic-compute-spot"
            }} if configs.ENVIRONMENT == "prod" else {}),
            containers=[
                client.V1Container(
                    name="agent",
                    image=configs.IMAGE,
                    image_pull_policy="Always",
                    env=[
                        client.V1EnvVar(name="ROOM_URL", value=room_url),
                        client.V1EnvVar(name="TOKEN", value=token),
                        client.V1EnvVar(name="LANGUAGE", value=language),
                        client.V1EnvVar(name="PORT", value=str(configs.PORT)),
                        client.V1EnvVar(name="HOST", value=configs.HOST),
                        client.V1EnvVar(name="UVICORN_RELOAD", value=str(configs.UVICORN_RELOAD).lower()),
                        client.V1EnvVar(name="UVICORN_LOG_LEVEL", value=configs.UVICORN_LOG_LEVEL),
                        client.V1EnvVar(name="DAILY_API_KEY", value=configs.DAILY_API_KEY or ""),
                        client.V1EnvVar(name="DAILY_SAMPLE_ROOM_URL", value=configs.DAILY_API_URL),
                        client.V1EnvVar(name="TTS_PROVIDER", value=configs.TTS_PROVIDER),
                        client.V1EnvVar(name="STT_PROVIDER", value=configs.STT_PROVIDER),
                        client.V1EnvVar(name="LLM_PROVIDER", value=configs.LLM_PROVIDER),
                        client.V1EnvVar(name="DEEPGRAM_API_KEY", value=configs.DEEPGRAM_API_KEY or ""),
                        client.V1EnvVar(name="OPENAI_API_KEY", value=configs.OPENAI_API_KEY or ""),
                        client.V1EnvVar(name="GOOGLE_API_KEY", value=configs.GOOGLE_API_KEY or ""),
                        client.V1EnvVar(name="CARTESIA_API_KEY", value=configs.CARTESIA_API_KEY or ""),
                        client.V1EnvVar(name="LLM_SERVICE", value=configs.LLM_SERVICE),
                        client.V1EnvVar(name="KOALA_ACCESS_KEY", value=configs.KOALA_ACCESS_KEY or ""),
                        client.V1EnvVar(name="AIC_ACCESS_KEY", value=configs.AIC_ACCESS_KEY or ""),
                        client.V1EnvVar(name="LIVEKIT_URL", value=configs.LIVEKIT_URL),
                        client.V1EnvVar(name="LIVEKIT_API_KEY", value=configs.LIVEKIT_API_KEY or ""),
                        client.V1EnvVar(name="LIVEKIT_API_SECRET", value=configs.LIVEKIT_API_SECRET or ""),
                        client.V1EnvVar(name="SARVAM_API_KEY", value=configs.SARVAM_API_KEY or ""),
                        client.V1EnvVar(name="ENABLE_KOALA_FILTER", value=str(configs.ENABLE_KOALA_FILTER).lower()),
                        client.V1EnvVar(name="ENABLE_AIC_FILTER", value=str(configs.ENABLE_AIC_FILTER).lower()),
                        client.V1EnvVar(name="AWS_REGION", value=configs.AWS_REGION),
                        client.V1EnvVar(name="ENABLE_RECORDING", value=str(configs.ENABLE_RECORDING).lower()),
                        client.V1EnvVar(name="S3_BUCKET_NAME", value=configs.S3_BUCKET_NAME),
                        client.V1EnvVar(name="ENABLE_S3_STORAGE", value=str(configs.ENABLE_S3_STORAGE).lower()),
                        client.V1EnvVar(name="ENABLE_LOCAL_STORAGE", value=str(configs.ENABLE_LOCAL_STORAGE).lower()),
                        client.V1EnvVar(name="ROUTER_URL", value=configs.ROUTER_URL),
                        client.V1EnvVar(name="MCP_SERVER_URL", value=configs.MCP_SERVER_URL),
                        client.V1EnvVar(name="ENABLE_TRACING", value=str(configs.ENABLE_TRACING).lower()),
                        client.V1EnvVar(name="LANGFUSE_BASE_URL", value=configs.LANGFUSE_BASE_URL),
                        client.V1EnvVar(name="LANGFUSE_SECRET_KEY", value=configs.LANGFUSE_SECRET_KEY),
                        client.V1EnvVar(name="LANGFUSE_PUBLIC_KEY", value=configs.LANGFUSE_PUBLIC_KEY),
                        client.V1EnvVar(
                            name="POD_NAME",
                            value_from=client.V1EnvVarSource(
                                field_ref=client.V1ObjectFieldSelector(field_path="metadata.name")
                            )
                        ),
                        client.V1EnvVar(
                            name="POD_IP",
                            value_from=client.V1EnvVarSource(
                                field_ref=client.V1ObjectFieldSelector(field_path="status.podIP")
                            )
                        ),
                    ],
                    resources=client.V1ResourceRequirements(
                        requests={
                            "cpu": POD_CPU,
                            "memory": POD_MEM,
                        },
                        limits={
                            "cpu": POD_CPU,
                            "memory": POD_MEM,
                        }
                    )
                )
            ]
        )
    )

    try:
        k8s.create_namespaced_pod(namespace=NAMESPACE, body=pod)
        logger.bind(sessionId=name).info(f"Created pod: {name}")
    except Exception as e:
        logger.bind(sessionId=name).error(f"Pod creation error: {e}")

    return name

def watch_pipecat_pods():
    w = watch.Watch()
    logger.info("Starting watcher for pipecat-agent-* pods...")

    while True:
        try:
            for event in w.stream(k8s.list_namespaced_pod,namespace=NAMESPACE,timeout_seconds=60):
                typ = event["type"]          # ADDED / MODIFIED / DELETED
                pod = event["object"]
                name = pod.metadata.name

                if not name.startswith("pipecat-agent-"):
                    continue

                pod_ip = pod.status.pod_ip

                if typ == "DELETED":
                    # Extract language from pod name (format: pipecat-agent-{pod_id}-{language})
                    language = None
                    if name and name.startswith("pipecat-agent-"):
                        parts = name.split("-")
                        if len(parts) >= 4: 
                            language = parts[-1] 

                    logger.bind(sessionId=name).warning(f"[WATCH] Pod deleted → {name} (language: {language})")

                    try:
                        # Use language-specific Redis key
                        if language:
                            redis_key = f"{REDIS_KEY_WARM_PODS}-{language}"
                        else:
                            redis_key = REDIS_KEY_WARM_PODS
                        
                        # Get all entries from the language-specific list
                        all_pods = redis_client.lrange(redis_key, 0, -1)
                        
                        # Find and remove the entry with matching pod_name
                        for pod_entry in all_pods:
                            try:
                                pod_data = json.loads(pod_entry)
                                if pod_data.get("pod_name") == name:
                                    # Remove this specific entry
                                    redis_client.lrem(redis_key, 0, pod_entry)
                                    logger.bind(sessionId=name).info(f"[WATCH] Removed pod from {redis_key}: {name}")
                                    break
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.bind(sessionId=name).warning(f"Error parsing pod entry: {e}")
                                continue
                        
                        async_thread(ensure_idle_pool)
                        logger.bind(sessionId=name).info(f"[WATCH] Pod deleted → {name}")
                    except Exception as e:
                        logger.bind(sessionId=name).error(f"Redis error when deleting pod: {e}")
                        continue
                    
        except Exception as e:
            logger.error(f"Error watching pods: {e}")
            time.sleep(1)
            continue
            

# def maintain_warm_pods():
#     while True:
#         try:
#             idle_count = redis_client.llen(REDIS_KEY_WARM_PODS)
#             if idle_count > MIN_IDLE:
#                 excess = idle_count - MIN_IDLE
#                 for _ in range(excess):
#                     pod = redis_client.rpop(REDIS_KEY_WARM_PODS)
#                     if pod:
#                         pod_info = json.loads(pod)
#                         delete_pod(pod_info["pod_name"], pod)
#         except Exception as e:
#             logger.error(f"Error maintaining warm pods: {e}")
#         time.sleep(300)  


@app.post("/driver/voice/connect")
async def assign_call(req: DriverParams):
    language_code = req.language_code
    while True:
        try:
            pod = redis_client.lpop(f"{REDIS_KEY_WARM_PODS}-{language_code}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection error when assigning call: {e}")
            raise HTTPException(status_code=503, detail="Redis unavailable. Service temporarily unavailable.")
        except Exception as e:
            logger.error(f"Redis error when assigning call: {e}")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

        if not pod:
            async_thread(ensure_idle_pool)
            raise HTTPException(status_code=503, detail="No warm pods available. Try again immediately.")

        pod_info = json.loads(pod)
        pod_endpoint = pod_info["endpoint"]
        pod_name = pod_info["pod_name"]
        room_url = pod_info["room_url"]
        token = pod_info["token"]

        # Check if pod exists in Kubernetes before making HTTP request
        try:
            k8s.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        except ApiException as e:
            if e.status == 404:
                logger.bind(sessionId=pod_name, userId=req.phoneNumber).warning(f"Pod {pod_name} not found in Kubernetes, removing from Redis and trying next")
                continue
            logger.bind(sessionId=pod_name, userId=req.phoneNumber).error(f"Kubernetes API error checking pod {pod_name}: {e}")
            continue
        except Exception as e:
            logger.bind(sessionId=pod_name, userId=req.phoneNumber).error(f"Error checking pod {pod_name}: {e}")
            continue

        async_thread(ensure_idle_pool)

        try:
            # daily_room_properties = DailyRoomProperties(
            #     exp=int(time.time() + configs.MAX_SESSION_TIME),
            #     eject_at_room_exp=True,
            # )
            # room = await daily_rest.create_room(
            #     params=DailyRoomParams(properties=daily_room_properties)
            # )
            # token_params = DailyMeetingTokenParams(
            #     properties=DailyMeetingTokenProperties(
            #         eject_after_elapsed=configs.MAX_SESSION_TIME,
            #     )
            # )

            # token = await daily_rest.get_token(
            #     room.url,
            #     expiry_time=configs.MAX_SESSION_TIME,
            #     eject_at_token_exp=True,
            #     owner=True,
            #     params=token_params,
            # )

            # async with httpx.AsyncClient(timeout=5) as client_http:
            #     response = await client_http.post(
            #         f"{pod_endpoint}/start-session",
            #         json={
            #             "phoneNumber": req.phoneNumber,
            #             "language_code": req.language_code,
            #             "current_version_of_app": req.current_version_of_app,
            #             "latest_version_of_app": req.latest_version_of_app,
            #             "agent_name": req.agent_name,
            #             "ride_id": req.ride_id,
            #             "room_url": room.url,
            #             "token": token
            #         }
            #     )
            #     response.raise_for_status()
            redis_client.rpush(REDIS_KEY_ACTIVE_PODS, json.dumps({
                "pod_name": pod_name,
                "endpoint": pod_endpoint
            }))
            logger.bind(sessionId=pod_name, userId=req.phoneNumber).info(f"Registered active pod → {pod_name}")
            return {"room_url": room_url, "token": token} 
        except Exception as e:
            logger.bind(sessionId=pod_name, userId=req.phoneNumber).error(f"Pod {pod_name} failed to accept start-session: {e}")
            active_entry = json.dumps({
                "pod_name": pod_name,
                "endpoint": pod_endpoint
            })
            async_thread(lambda: delete_pod(pod_name, active_entry))
            raise HTTPException(status_code=500, detail="Pod failed. Retrying recommended.")



@app.post("/register")
async def register_pod(req: RegisterReq):
    """Pod calls this when it starts."""
    
    # Extract language from pod name (format: pipecat-agent-{pod_id}-{language})
    language = None
    if req.pod_name and req.pod_name.startswith("pipecat-agent-"):
        parts = req.pod_name.split("-")
        if len(parts) >= 4: 
            language = parts[-1] 
    
    logger.info(f"language: {language}")

    # async with httpx.AsyncClient(timeout=5) as client_http:
    #     response = await client_http.post(
    #         f"{req.endpoint}/start-session",
    #         json={
    #             "language_code": language,
    #             "room_url": room.url,
    #             "token": token,
    #         }
    #     )
    #     response.raise_for_status() 


    try:
        # Use dynamic Redis key based on language
        if language:
            redis_key = f"{REDIS_KEY_WARM_PODS}-{language}"
        else:
            redis_key = REDIS_KEY_WARM_PODS  # Fallback to base key if language not found
        
        redis_client.rpush(redis_key, json.dumps({
            "pod_name": req.pod_name,
            "endpoint": req.endpoint,
            "room_url": req.room_url,
            "token": req.token,
        }))

        logger.bind(sessionId=req.pod_name).info(f"Registered warm pod → {req.pod_name} (language: {language}, redis_key: {redis_key})")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.bind(sessionId=req.pod_name).error(f"Redis connection error when registering pod: {e}")
        return {"status": "registered", "warning": "Redis unavailable, registration may not "}
    except Exception as e:
        logger.bind(sessionId=req.pod_name).error(f"Redis error when registering pod: {e}")
        return {"status": "registered", "warning": "Redis error, registration may not persist"}

    return {"status": "registered"}



@app.post("/session-ended")
def end_call(req: EndReq):
    """Pod notifies pod_manager it is done. Pod Manager deletes pod."""
    logger.bind(sessionId=req.pod_name).info(f"Deleting pod after session → {req.pod_name}")
    active_entry = json.dumps({
        "pod_name": req.pod_name,
        "endpoint": req.endpoint
    })
    async_thread(lambda: delete_pod(req.pod_name, active_entry))
    return {"status": "deleted"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint - returns 200 only when pod manager is ready."""
    if check_pod_manager_ready():
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Pod manager not ready")


def check_pod_manager_ready():
    """Check if pod manager is ready to accept requests."""
    try:
        # Check Redis connection
        redis_client.ping()
        
        # Check Kubernetes API connection
        k8s.list_namespaced_pod(namespace=NAMESPACE, limit=1)
        
        return True
    except Exception as e:
        logger.debug(f"Pod manager not ready yet: {e}")
        return False


def wait_for_readiness():
    """Wait until pod manager is ready, then start background tasks."""
    max_retries = 60  # Wait up to 5 minutes (60 * 5 seconds)
    retry_count = 0
    
    while retry_count < max_retries:
        if check_pod_manager_ready():
            logger.info("Pod manager is ready. Starting background tasks...")
            async_thread(ensure_idle_pool)
            async_thread(watch_pipecat_pods)
            return
        
        retry_count += 1
        logger.debug(f"Waiting for pod manager to be ready... (attempt {retry_count}/{max_retries})")
        time.sleep(5)  # Wait 5 seconds between checks
    
    logger.error("Pod manager failed to become ready after maximum retries. Starting background tasks anyway...")
    # Start anyway after max retries to avoid complete failure
    async_thread(ensure_idle_pool)
    async_thread(watch_pipecat_pods)


@app.on_event("startup")
def startup_event():
    logger.debug("Starting up... waiting for pod manager to be ready")
    async_thread(wait_for_readiness)
    # async_thread(maintain_warm_pods)

