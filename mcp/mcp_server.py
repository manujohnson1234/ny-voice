#!/usr/bin/env python3
"""Main FastAPI application entry point for Namma Yatri MCP Server."""
import uvicorn
from fastapi import FastAPI

from config import AppConfig
from routes import register_routes

# Initialize FastAPI app
app = FastAPI(title=AppConfig.TITLE, version=AppConfig.VERSION)

# Register all routes
register_routes(app)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        log_level="info"
    )
