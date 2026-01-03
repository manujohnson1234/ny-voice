import httpx
import json
import os
from loguru import logger
from pipecat.services.llm_service import FunctionCallParams
from app.core.session_manager import get_session_manager

from typing import Dict

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
            return {"success": False, "error": f"Failed to call {tool_name}: {e}"}




class RC_DL_IssuesHandlers:

    @staticmethod
    async def get_doc_status_handler(params: FunctionCallParams, session_id: str = None):
        """Handler for get_doc_status tool"""
        session_manager = get_session_manager()

        if not session_id:
            logger.error("Session ID is missing")
            error_result = {
                "success": False,
                "error": True
            }
            await params.result_callback(error_result)
            return
        
        mobile_number = await session_manager.get_value(session_id, "driver_number")

        if not mobile_number:
            logger.error(f"driver_number not found in session {session_id}")
            error_result = {
                "success": False,
                "error": True
            }
            await params.result_callback(error_result)
            return

        result = await call_mcp_tool("get_doc_status", {"mobile_number": mobile_number})

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
    