from pipecat.services.llm_service import LLMService
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from app.core.session_manager import get_session_manager
from app.agents.voice.driver.llm import get_llm_service
from app.agents.voice.driver.agents.rc_dl_issues.function_handler import RC_DL_IssuesHandlers
from app.agents.voice.driver.agents.rc_dl_issues.system_prompt import get_rc_dl_issues_system_prompt
from app.agents.voice.driver.agents.rc_dl_issues.tool_schema import get_rc_dl_issues_tool_schema


class RC_DL_IssuesAgent:
    def __init__(self, session_id: str, language: str = "ta"):
        self.session_id = session_id
        self.language = language
        self.session_manager = get_session_manager()

        self._handlers = RC_DL_IssuesHandlers()

        self.llm = get_llm_service()

        self._register_tools()

    def _register_tools(self):

        async def get_doc_status_wrapper(params):
            return await self._handlers.get_doc_status_handler(params, session_id=self.session_id)
        
        async def bot_fail_to_resolve_wrapper(params):
            return await self._handlers.bot_fail_to_resolve_handler(params, session_id=self.session_id)
        
        self.llm.register_function("get_doc_status", get_doc_status_wrapper)
        self.llm.register_function("bot_fail_to_resolve", bot_fail_to_resolve_wrapper)

    def get_llm(self) -> LLMService:
        return self.llm
        
    def get_system_prompt(self) -> str:
        return get_rc_dl_issues_system_prompt(language=self.language)

    def get_tools(self) -> ToolsSchema:
        return get_rc_dl_issues_tool_schema()