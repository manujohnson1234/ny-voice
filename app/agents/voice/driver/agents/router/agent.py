from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type


from loguru import logger

from pipecat.services.llm_service import FunctionCallParams, LLMService
from pipecat.processors.aggregators.llm_context import LLMContext, NOT_GIVEN
from pipecat.pipeline.service_switcher import ServiceSwitcherStrategyManual, StrategyType, ServiceSwitcher
from pipecat.pipeline.llm_switcher import LLMSwitcher
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.frames.frames import FunctionCallResultProperties

from app.agents.voice.driver.llm import get_llm_service
from app.core.session_manager import get_session_manager


from app.agents.voice.driver.agents.router.system_prompt import get_agent_system_prompt
from app.agents.voice.driver.agents.router.tool_schema import get_router_tool_schema


@dataclass 
class AgentConfig:
    agentName: str
    description: str
    system_prompt: str
    tools: Optional[List[FunctionSchema]] = None

class AgentRouter(LLMSwitcher):
    def __init__(
        self, 
        agents: List[Tuple[LLMService, AgentConfig]], 
        initial_agent: str = "router",
        session_id: str = None
    ):
        self.session_id = session_id
        self.session_manager = get_session_manager()
        self.current_agent = initial_agent
        self.router_llm = get_llm_service()
        
        # Build agents dict

        self.router_tool_schema = get_router_tool_schema()
        self.router_system_prompt = get_agent_system_prompt()


        self.agents_dict: Dict[str, AgentConfig] = {
            "router": AgentConfig(
                agentName="router",
                description="Routes conversations to specialized agents",
                system_prompt=self.router_system_prompt,
                tools=self.router_tool_schema  # List[FunctionSchema], not ToolsSchema
            )
        }
        
        # Build LLM mapping
        self.llm_by_agent: Dict[str, LLMService] = {"router": self.router_llm}
        llm_list = [self.router_llm]
        
        for (llm, config) in agents:
            self.agents_dict[config.agentName] = config
            self.llm_by_agent[config.agentName] = llm
            llm_list.append(llm)
        
        # Build contexts
        self.contexts: Dict[str, Tuple[Any, Optional[List[FunctionSchema]]]] = {}
        for agent_name, config in self.agents_dict.items():
            if config.tools:
                config.tools.append(self.router_tool_schema[0])
                
            self.contexts[agent_name] = (
                config.system_prompt,
                config.tools if config.tools else None,
            )
        
        super().__init__(llms=llm_list, strategy_type=ServiceSwitcherStrategyManual)

        self._register_event_handler("on_agent_switched")


        self._register_switch_tool()


        self._update_filters(self.llm_by_agent[self.current_agent])


    def _register_switch_tool(self):
        
        for llm_agent in self.llm_by_agent.values():
            llm_agent.register_function("change_agent", self._handle_switch)



    async def _handle_switch(self, params: FunctionCallParams):
        target_agent = params.arguments.get("agent_name")

        logger.info(f"Switching to agent: {target_agent}")
        
        # Get agents from session manager
        agents = self.agents_dict
        
        if target_agent not in agents:
            logger.error(f"Unknown agent: {target_agent}")
            await params.result_callback({"error": f"Unknown agent: {target_agent}"})
            return
        
        # Update current agent in session
        self.current_agent = target_agent
        
        # Get LLM for target agent and switch
        target_llm = self.llm_by_agent[target_agent]
        self.strategy.active_service = target_llm
        
        self._update_filters(target_llm)
        

        async def on_context_updated_after_switch():
            logger.info("Context updated after agent switch - appending user message")

            await self._call_event_handler("on_agent_switched")



        return await params.result_callback(None,properties=FunctionCallResultProperties(run_llm=False,on_context_updated=on_context_updated_after_switch))

    def _update_filters(self, target_llm: LLMService):
        if hasattr(self, '_pipelines'):
            for pipeline in self._pipelines:
                for processor in pipeline.processors:
                    if isinstance(processor, ServiceSwitcher.ServiceSwitcherFilter):
                        processor._active_service = target_llm

    def get_current_agent_name(self) -> str:
        return self.current_agent

    def get_system_prompt(self) -> str:
        return get_agent_system_prompt(language=self.language)
    
    def get_tools(self) -> ToolsSchema:
        return get_router_tool_schema()

    def get_current_context(self) -> Any:
        # Return a COPY of the list to prevent mutation of the original
        return list(self.contexts[self.current_agent][0])

    def get_current_tools(self) -> ToolsSchema:
        tools: List[FunctionSchema] = []
        for config in self.contexts.values():
            if config[1]:
                tools.extend(config[1])
        return ToolsSchema(standard_tools=tools) if tools else NOT_GIVEN

