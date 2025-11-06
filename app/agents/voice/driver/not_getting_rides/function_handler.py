import httpx
import json
import os
from loguru import logger
from pipecat.services.llm_service import FunctionCallParams
from app.core.session_manager import get_session_manager

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

async def get_driver_info_handler(params: FunctionCallParams, session_id: str = None):
    """Handler for get_driver_info tool"""
    session_manager = get_session_manager()
    
    # Retrieve driver_number from session if session_id is provided
    if not session_id:
        logger.error("Session ID is missing")
        error_result = {
            "success": False,
            "error": True
        }
        await params.result_callback(error_result)
        return
    
    driver_number = await session_manager.get_value(session_id, "driver_number")
    if not driver_number:
        logger.error(f"driver_number not found in session {session_id}")
        error_result = {
            "success": False,
            "error": True
        }
        await params.result_callback(error_result)
        return
    
    logger.info(f"Retrieved driver_number {driver_number} from session {session_id}")
    mobile_number = driver_number
    
    result = await call_mcp_tool("get_driver_info", {"mobile_number": mobile_number})

    logger.info(f"Result from get_driver_info: {result}")
    
    # Extract driverId from result and store in session
    # Response structure: {'success': True, 'result': {'success': True, 'driverId': '...', ...}}
    if session_id and result:
        driver_id = None
        if isinstance(result, dict):
            # Check if result has a nested 'result' key
            nested_result = result.get("result", {})
            if isinstance(nested_result, dict):
                driver_id = nested_result.get("driverId")
            
            # Also check top level in case structure is different
            if not driver_id:
                driver_id = result.get("driverId")
        
        if driver_id:
            await session_manager.set_value(session_id, "driver_id", driver_id)
            logger.info(f"Stored driver_id {driver_id} in session {session_id}")
        else:
            logger.error(f"driverId not found in result for session {session_id}. Result: {result}")
    
    await params.result_callback(result)

async def send_dummy_notification_handler(params: FunctionCallParams, session_id: str = None):
    """Handler for send_dummy_notification tool"""
    session_manager = get_session_manager()
    
    # Retrieve driver_id from session if session_id is provided
    if not session_id:
        logger.error("Session ID is missing")
        error_result = {
            "success": False,
            "error": True
        }
        await params.result_callback(error_result)
        return
    
    driver_id = await session_manager.get_value(session_id, "driver_id")
    if not driver_id:
        logger.error(f"driver_id not found in session {session_id}")
        error_result = {
            "success": False,
            "error": True
        }
        await params.result_callback(error_result)
        return
    
    logger.info(f"Retrieved driver_id {driver_id} from session {session_id}")
    result = await call_mcp_tool("send_dummy_notification", {"driver_id": driver_id})
    await params.result_callback(result)


async def send_overlay_sms_handler(params: FunctionCallParams, session_id: str = None):
    """Handler for send_dues_overlay tool"""
    session_manager = get_session_manager()
    
    # Retrieve driver_id from session if session_id is provided
    if not session_id:
        logger.error("Session ID is missing")
        error_result = {
            "success": False,
            "error": True
        }
        await params.result_callback(error_result)
        return
    
    driver_id = await session_manager.get_value(session_id, "driver_id")
    if not driver_id:
        logger.error(f"driver_id not found in session {session_id}")
        error_result = {
            "success": False,
            "error": True
        }
        await params.result_callback(error_result)
        return
    
    logger.info(f"Retrieved driver_id {driver_id} from session {session_id}")
    result = await call_mcp_tool("send_overlay_sms", {"driver_id": driver_id})
    await params.result_callback(result)