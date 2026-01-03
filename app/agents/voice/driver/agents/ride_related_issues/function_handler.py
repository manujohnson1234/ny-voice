import httpx
import json
import os
from typing import Dict
from loguru import logger

from pipecat.services.llm_service import FunctionCallParams
from app.core.session_manager import get_session_manager


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

async def call_mcp_tool(tool_name: str, parameters: dict = None):
    """Call MCP server tool"""
    async with httpx.AsyncClient(timeout=25) as client:
        try:
            payload = {
                "tool": tool_name,
                "parameters": parameters or {}
            }
            response = await client.post(f"{MCP_SERVER_URL}/call-tool", json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                nested_result = data.get("result")
                if isinstance(nested_result, dict):
                    return nested_result
            return data
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")



class RideIssueHandlers:

    @staticmethod
    async def get_ride_details_handler(params: FunctionCallParams, session_id: str = None):
        session_manager = get_session_manager()

        if not session_id:
            logger.error("Session ID is missing")
            error_result = {
                "success": False,
                "error": True
            }
            await params.result_callback(error_result)
            return

        ride_id = await session_manager.get_value(session_id, "ride_id")
        issue_type = params.arguments.get("issue") 

        if not ride_id:
            logger.error("ride_id not found in session")
            error_result = {
                "success": False,
                "error": True
            }
            await params.result_callback(error_result)
            return

        result = await call_mcp_tool("get_ride_details", {"ride_id": ride_id, "issue_type": issue_type})
        await params.result_callback(result)

    @staticmethod
    async def bot_fail_to_resolve_handler(params: FunctionCallParams, session_id: str = None):
        """Handler for bot_fail_to_resolve tool"""
        session_manager = get_session_manager()
        
        if not session_id:
            logger.error("Session ID is missing")
            error_result = {
                "success": False,
                "error": True
            }
            await params.result_callback(error_result)
            return
        
        await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
        await session_manager.set_value(session_id, "reason", "driver_asked_to_call_agent")
        
        result = {
            "success": True,
            "message": "Escalating to support team"
        }
        await params.result_callback(result)

    def get_all_handlers(self) -> Dict[str, callable]:
        """
        Get a dictionary mapping function names to their handlers.
        """
        return {
            "get_ride_details": self.get_ride_details_handler,
            "bot_fail_to_resolve": self.bot_fail_to_resolve_handler
        }
