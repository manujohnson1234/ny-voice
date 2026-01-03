from typing import Optional

from loguru import logger

from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.llm_service import LLMService
from pipecat.adapters.schemas.tools_schema import ToolsSchema

from app.core.session_manager import get_session_manager
from app.agents.voice.driver.llm import get_llm_service
from app.agents.voice.driver.agents.not_getting_rides.function_handler import NotGettingRidesHandlers
from app.agents.voice.driver.agents.not_getting_rides.system_prompt import get_not_getting_rides_system_prompt
from app.agents.voice.driver.agents.not_getting_rides.tool_schema import get_not_getting_rides_tool_schema



class NotGettingRidesAgent:

    def __init__(self, session_id: str, language: str = "ta"):
        self.session_id = session_id
        self.language = language
        self.session_manager = get_session_manager()

        self._handlers = NotGettingRidesHandlers()

        self.llm = get_llm_service()

        self._register_tools()

    def _register_tools(self):

        async def get_driver_info_wrapper(params):
            return await self._handlers.get_driver_info_handler(params, session_id=self.session_id)
        
        async def send_dummy_notification_wrapper(params):
            return await self._handlers.send_dummy_notification_handler(params, session_id=self.session_id)
        
        async def send_overlay_sms_wrapper(params):
            return await self._handlers.send_overlay_sms_handler(params, session_id=self.session_id)
        
        async def bot_fail_to_resolve_wrapper(params):
            return await self._handlers.bot_fail_to_resolve_handler(params, session_id=self.session_id)


        self.llm.register_function("get_driver_info", get_driver_info_wrapper)
        self.llm.register_function("send_dummy_notification", send_dummy_notification_wrapper)
        self.llm.register_function("send_overlay_sms", send_overlay_sms_wrapper)
        self.llm.register_function("bot_fail_to_resolve", bot_fail_to_resolve_wrapper)

    def get_llm(self) -> LLMService:
        return self.llm

    def get_system_prompt(self) -> str:
        return get_not_getting_rides_system_prompt(language=self.language)

    def get_tools(self) -> ToolsSchema:
        return get_not_getting_rides_tool_schema()