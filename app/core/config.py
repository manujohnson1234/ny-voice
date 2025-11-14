import os

from dotenv import load_dotenv
from loguru import logger

load_dotenv()



PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
UVICORN_RELOAD = os.environ.get("UVICORN_RELOAD", "true").lower() == "true"
UVICORN_LOG_LEVEL = os.environ.get("UVICORN_LOG_LEVEL", "info")


DAILY_API_KEY = os.environ.get("DAILY_API_KEY")
DAILY_API_URL = os.environ.get("DAILY_SAMPLE_ROOM_URL", "https://api.daily.co/v1/")


TTS_PROVIDER=os.environ.get("TTS_PROVIDER", "sarvam")
STT_PROVIDER=os.environ.get("STT_PROVIDER", "openai")
LLM_PROVIDER=os.environ.get("LLM_PROVIDER", "openai")

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")

LLM_SERVICE = os.environ.get("LLM_SERVICE", "openai")

KOALA_ACCESS_KEY = os.environ.get("KOALA_ACCESS_KEY")

AIC_ACCESS_KEY = os.environ.get("AIC_ACCESS_KEY")


LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://livekit.yourdomain.com")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")

ENABLE_KOALA_FILTER = os.environ.get("ENABLE_KOALA_FILTER", "false").lower() == "true"
ENABLE_AIC_FILTER = os.environ.get("ENABLE_AIC_FILTER", "false").lower() == "true"


MAX_SESSION_TIME = 5 * 60  # seconds or whatever you want