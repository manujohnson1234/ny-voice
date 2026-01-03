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


class NotGettingRidesHandlers:


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

        
        
        count_tool_calls = await session_manager.get_value(session_id, "count_tool_calls")
        count_tool_calls["get_driver_info"] = count_tool_calls.get("get_driver_info", 0) + 1
        if count_tool_calls["get_driver_info"] > 3:
            await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
            await session_manager.set_value(session_id, "reason", "error_due_to_mcp_or_common")
            return
        
        driver_number = await session_manager.get_value(session_id, "driver_number")
        time_till_not_getting_rides = None
        time_quantity = None
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

        time_till_not_getting_rides = int(params.arguments.get("time_till_not_getting_rides"))
        time_quantity = params.arguments.get("time_quantity")

        logger.info(f"time_till_not_getting_rides: {time_till_not_getting_rides}, time_quantity: {time_quantity}")

        result = await call_mcp_tool("get_driver_info", {"mobile_number": mobile_number, "time_till_not_getting_rides": time_till_not_getting_rides, "time_quantity": time_quantity})

        if isinstance(result, dict):
            if result.get("success") == False:
                logger.info("error in get_driver_info result")
                await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
                await session_manager.set_value(session_id, "reason", "error_due_to_mcp_or_common")
                return

        logger.info(f"Result from get_driver_info: {result}")
        
        # Extract driverId from result and store in session
        # Response structure: {'success': True, 'result': {'success': True, 'driverId': '...', ...}}
        if session_id and result:
            driver_id = None
            if isinstance(result, dict):
                # Check if result has a nested 'result' key
                # nested_result = result.get("result", {})
                # if isinstance(nested_result, dict):
                driver_id = result.get("driverId")
                
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
        
        count_tool_calls = await session_manager.get_value(session_id, "count_tool_calls")
        count_tool_calls["send_dummy_notification"] = count_tool_calls.get("send_dummy_notification", 0) + 1
        if count_tool_calls["send_dummy_notification"] > 3:
            await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
            await session_manager.set_value(session_id, "reason", "error_due_to_mcp_or_common")
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
        if isinstance(result, dict):
            if result.get("success") == False:
                await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
                await session_manager.set_value(session_id, "reason", "error_due_to_mcp_or_common")
                return
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

        count_tool_calls = await session_manager.get_value(session_id, "count_tool_calls")
        count_tool_calls["send_overlay_sms"] = count_tool_calls.get("send_overlay_sms", 0) + 1
        if count_tool_calls["send_overlay_sms"] > 3:
            await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
            await session_manager.set_value(session_id, "reason", "error_due_to_mcp_or_common")
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
        if isinstance(result, dict):
            if result.get("success") == False:
                await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
                await session_manager.set_value(session_id, "reason", "error_due_to_mcp_or_common")
                return
        await params.result_callback(result)     



    async def bot_fail_to_resolve_handler(params: FunctionCallParams, session_id: str = None):
        """Handler for bot_fail_to_resolve tool"""
        session_manager = get_session_manager()
        await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
        await session_manager.set_value(session_id, "reason", "driver_asked_to_call_agent")
        return


    def get_all_handlers(self) -> Dict[str, callable]:
        """
        Get a dictionary mapping function names to their handlers.
        """
        return {
            "get_driver_info": self.get_driver_info_handler,
            "send_dummy_notification": self.send_dummy_notification_handler,
            "send_overlay_sms": self.send_overlay_sms_handler,
            "bot_fail_to_resolve": self.bot_fail_to_resolve_handler
        }