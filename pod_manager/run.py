import os

import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import configs

if __name__ == "__main__":
    uvicorn.run(
        "pod_manager:app",  # Path to the FastAPI app object in pod_manager.py
        host=configs.HOST,
        port=configs.PORT,
        reload=configs.UVICORN_RELOAD,
        log_level=configs.UVICORN_LOG_LEVEL,
    )

