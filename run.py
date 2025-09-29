import os

import uvicorn
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

from app.core.config import HOST, PORT, UVICORN_LOG_LEVEL, UVICORN_RELOAD


if __name__ == "__main__":
    logger.info(f"Starting Uvicorn server on {HOST}:{PORT}")
    logger.info(f"Reload enabled: {UVICORN_RELOAD}")
    logger.info(f"Log level: {UVICORN_LOG_LEVEL}")
    logger.info("Running the main application.")
    uvicorn.run(
        "app.main:app",  # Path to the FastAPI app object in app/main.py
        host=HOST,
        port=PORT,
        reload=UVICORN_RELOAD,
        log_level=UVICORN_LOG_LEVEL,
        log_config=None,  # Disable Uvicorn's default logging config
        access_log=True,  # Keep access logs but route through our interceptor
    )