import httpx
import json
import os
from loguru import logger
from pipecat.services.llm_service import FunctionCallParams

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

async def call_mcp_tool(tool_name: str, parameters: dict = None):
    """Call MCP server tool"""
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "tool": tool_name,
                "parameters": parameters or {}
            }
            response = await client.post(f"{MCP_SERVER_URL}/call-tool", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return {"success": False, "error": f"Failed to call {tool_name}: {str(e)}"}

async def get_driver_info_handler(params: FunctionCallParams):
    """Handler for get_driver_info tool"""
    # logger.info(f"get_driver_info_handler called with mobileNumber: {mobile_number}")
    mobile_number = "8610263112"
    result = await call_mcp_tool("get_driver_info", {"mobile_number": mobile_number})
    await params.result_callback(result)

async def send_dummy_notification_handler(params: FunctionCallParams):
    """Handler for send_dummy_notification tool"""
    # logger.info(f"send_dummy_notification_handler called with driver_id: {params.parameters}")
    driver_id = "60580e5a-a7fe-4169-87ed-0b80eddf09ea"
    result = await call_mcp_tool("send_dummy_notification", {"driver_id": driver_id})
    await params.result_callback(result)
    