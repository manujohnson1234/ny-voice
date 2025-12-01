import asyncio
import uuid
import json
import time
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from kubernetes import client, config
from pydantic import BaseModel
import redis
import httpx
import threading
import os
from loguru import logger

import configs

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
except:
    config.load_kube_config()
k8s = client.CoreV1Api()


app = FastAPI(title="NY Voice Pod Manager")



class DriverParams(BaseModel):
    phoneNumber: str
    language_code: Optional[str] = None
    current_version_of_app: Optional[str] = None
    latest_version_of_app: Optional[str] = None

class RegisterReq(BaseModel):
    pod_name: str
    endpoint: str   # pod internal URL (http://ip:8080)

class EndReq(BaseModel):
    pod_name: str



def async_thread(fn):
    """Runs a function in a separate thread non-blocking."""
    t = threading.Thread(target=fn, daemon=True)
    t.start()






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
        active_count = redis_client.llen(REDIS_KEY_ACTIVE_PODS) 
        idle_count = redis_client.llen(REDIS_KEY_WARM_PODS)

        total_pods = active_count + idle_count

        if total_pods +  >= MAX_POD:
            logger.info(f"Max pods reached: {total_pods} active pods")
            return

        to_create = MIN_IDLE - idle_count

        if to_create > 0:
            logger.info(f"Ensuring warm pool: {idle_count} idle, creating {to_create} pods")
            for _ in range(to_create):
                async_thread(create_pod)
        else:
            logger.info(f"Warm pool sufficient: {idle_count} idle pods")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(f"Redis connection issue during pool check: {e}")
    except Exception as e:
        logger.error(f"Error ensuring idle pool: {e}")

def delete_pod(name: str):
    try:
        k8s.delete_namespaced_pod(
            name=name,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions()
        )
        try:
            redis_client.lrem(REDIS_KEY_ACTIVE_PODS, 0, name)
            async_thread(ensure_idle_pool())
        except Exception as e:
            logger.error(f"Redis error when deleting pod: {e}")
        logger.info(f"Pod deleted: {name}")
    except Exception as e:
        logger.error(f"Pod delete error: {e}")




def create_pod():
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
    
    name = f"pipecat-agent-{pod_id}"

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=name,
            labels={"app": "pipecat-agent"}
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[
                client.V1Container(
                    name="agent",
                    image=configs.IMAGE,
                    image_pull_policy="Always",
                    env=[
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
        logger.info(f"Created pod: {name}")
    except Exception as e:
        logger.error(f"Pod creation error: {e}")

    return name




@app.post("/driver/voice/connect")
async def assign_call(req: DriverParams):
    try:
        pod = redis_client.lpop(REDIS_KEY_WARM_PODS)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error(f"Redis connection error when assigning call: {e}")
        raise HTTPException(status_code=503, detail="Redis unavailable. Service temporarily unavailable.")
    except Exception as e:
        logger.error(f"Redis error when assigning call: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    if not pod:
        # No idle pods → create one and queue this call
        # async_thread(create_pod)
        raise HTTPException(status_code=503, detail="No warm pods available. Try again immediately.")

    pod_info = json.loads(pod)
    pod_endpoint = pod_info["endpoint"]
    pod_name = pod_info["pod_name"]

    async_thread(ensure_idle_pool)

    try:
        async with httpx.AsyncClient(timeout=5) as client_http:
            response = await client_http.post(
                f"{pod_endpoint}/start-session",
                json={
                    "phoneNumber": req.phoneNumber,
                    "language_code": req.language_code,
                    "current_version_of_app": req.current_version_of_app,
                    "latest_version_of_app": req.latest_version_of_app
                }
            )
            response.raise_for_status()
            redis_client.rpush(REDIS_KEY_ACTIVE_PODS, json.dumps({
                "pod_name": req.pod_name,
                "endpoint": req.endpoint
            }))
        logger.info(f"Registered active pod → {req.pod_name}")
            return response.json()
    except Exception as e:
        logger.error(f"Pod {pod_name} failed to accept start-session: {e}")
        # pod becomes invalid, delete it
        async_thread(lambda: delete_pod(pod_name))
        raise HTTPException(status_code=500, detail="Pod failed. Retrying recommended.")



@app.post("/register")
def register_pod(req: RegisterReq):
    """Pod calls this when it starts."""
    try:
        redis_client.rpush(REDIS_KEY_WARM_PODS, json.dumps({
            "pod_name": req.pod_name,
            "endpoint": req.endpoint
        }))
        logger.info(f"Registered warm pod → {req.pod_name}")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.error(f"Redis connection error when registering pod: {e}")
        # Still return success to avoid pod retrying registration
        return {"status": "registered", "warning": "Redis unavailable, registration may not persist"}
    except Exception as e:
        logger.error(f"Redis error when registering pod: {e}")
        return {"status": "registered", "warning": "Redis error, registration may not persist"}

    return {"status": "registered"}



@app.post("/session-ended")
def end_call(req: EndReq):
    """Pod notifies pod_manager it is done. Pod Manager deletes pod."""
    logger.info(f"Deleting pod after session → {req.pod_name}")

    async_thread(lambda: delete_pod(req.pod_name))
    return {"status": "deleted"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "healthy"}


@app.on_event("startup")
def startup_event():
    logger.info("Starting up... ensuring warm pool")
    # Run in background thread to avoid blocking startup if Redis is slow/unavailable
    async_thread(ensure_idle_pool)

