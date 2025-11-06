from dataclasses import dataclass
from typing import Dict, Tuple, Type, Optional
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import Frame, LLMContextFrame, LLMRunFrame, ManuallySwitchServiceFrame
from pipecat.pipeline.llm_switcher import LLMSwitcher
from pipecat.pipeline.service_switcher import (
    ServiceSwitcher,
    ServiceSwitcherStrategyManual,
    StrategyType,
)
from pipecat.processors.aggregators.llm_context import LLMContext, NOT_GIVEN
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import FunctionCallParams, LLMService



@dataclass
class AgentConfig:
    name: str
    description: str
    system_prompt: str
    tools: Optional[ToolsSchema] = None



class AgentRouter(LLMSwitcher):
    """Router for routing requests to the appropriate agent.

    Parameters:
        agents: List of agents to route requests to.
    """

    def __init__(
        self,
        agents: Dict[str, Tuple[LLMService, AgentConfig]],
        initial_agent: str,
        message_transfer_count: int = 5,
        strategy_type: Type[StrategyType] = ServiceSwitcherStrategyManual,
    ):
        if initial_agent not in agents:
            raise ValueError(f"Initial agent '{initial_agent}' not found in agents dictionary")
        
        self._agent_configs: Dict[str, AgentConfig] = {}
        self._agent_contexts: Dict[str, LLMContext] = {}
        self._current_agent: str = initial_agent
        self._message_transfer_count: int = message_transfer_count
        # Reverse mapping: LLM instance -> agent name (for debugging and lookups)
        self._llm_to_agent: Dict[LLMService, str] = {}
        # Reference to context aggregator (set from bot.py)
        self._context_aggregator = None

        llm_list = []

        for agent_name, (llm, config) in agents.items():
            self._agent_configs[agent_name] = config
            llm_list.append(llm)
            self._llm_to_agent[llm] = agent_name
            # get the tools and the system prompt from the agent config
            self._agent_contexts[agent_name] = LLMContext(
                messages=[{"role": "system", "content": config.system_prompt}],
                tools=config.tools or NOT_GIVEN,
            )
            logger.info(f"Agent context for {agent_name}: {self._agent_contexts[agent_name].get_messages()}")
        # Initialize parent LLMSwitcher with specified strategy
        super().__init__(llms=llm_list, strategy_type=strategy_type)


        # Register event handler for agent switching
        self._register_event_handler("on_agent_switched")


        # Register function handlers for each agent
        self._register_handoff_function()

        # Activate initial agent
        self._set_active_agent(initial_agent)

    
    def _register_handoff_function(self):
        """Register handoff_to_agent function on all LLM agents.

        Creates a dynamic function schema listing all available agents and
        registers the handoff handler on every LLM in the router.
        """
        # Build schema with available agents
        agent_descriptions = [
            f"- {name}: {config.description}"
            for name, config in self._agent_configs.items()
        ]

        handoff_schema = FunctionSchema(
            name="handoff_to_agent",
            description=f"""Transfer conversation to a specialized agent.
Available agents:
{chr(10).join(agent_descriptions)}""",
            properties={
                "agent_name": {
                    "type": "string",
                    "enum": list(self._agent_configs.keys()),
                    "description": "Name of the agent to transfer to",
                },
                "context_summary": {
                    "type": "string",
                    "description": "Brief summary of the conversation so far (optional)",
                },
            },
            required=["agent_name"],
        )

        # Add handoff tool to each agent's context
        for agent_name, context in self._agent_contexts.items():
            existing_tools = context.tools if context.tools is not NOT_GIVEN else None

            if existing_tools:
                # Merge with existing tools
                from loguru import logger
                logger.info(f"Existing tools: {existing_tools}")
                logger.info(f"agent_name: {agent_name}")
                all_tools = list(existing_tools.standard_tools) + [handoff_schema]
                context.set_tools(ToolsSchema(standard_tools=all_tools))
            else:
                # Just set handoff tool
                context.set_tools(ToolsSchema(standard_tools=[handoff_schema]))

        # Register handler on all LLMs (inherited from parent's llms list)
        for llm in self.llms:
            llm.register_function("handoff_to_agent", self._handle_handoff)

        logger.debug(f"Registered handoff_to_agent function on {len(self.llms)} LLMs")




    async def _handle_handoff(self, params: FunctionCallParams):
        target_agent = params.arguments.get("agent_name")
        summary = params.arguments.get("context_summary", "")
       

        logger.info(
            f"Handoff requested from '{self._current_agent}' to '{target_agent}'"
            + (f" with summary: {summary}" if summary else "")
        )

        if target_agent not in self._agent_configs:
            error_msg = f"Unknown agent: {target_agent}"
            logger.error(error_msg)
            await params.result_callback({"success": False, "error": error_msg})
            return
        

        logger.debug(f"Handing off from '{self._current_agent}' to '{target_agent}' - context will be cleared")

        target_context = self._agent_contexts[target_agent]

        logger.info(f"Target context: {target_context}")


        target_config = self._agent_configs[target_agent]

        old_active_agent = self._current_agent

        self._current_agent = target_agent
        

        target_context.set_messages(
            [{"role": "system", "content": target_config.system_prompt}]
        )
        
        logger.debug(f"Cleared context for '{target_agent}' - ready for event handler to add greeting")
        target_llm = self._get_llm_by_name(target_agent)


        self.strategy.active_service = target_llm

        
        if hasattr(self, '_pipelines'):
            for pipeline in self._pipelines:
                for processor in pipeline.processors:
                    if isinstance(processor, ServiceSwitcher.ServiceSwitcherFilter):
                        logger.info(f"Setting active service for {processor} to {target_llm}")
                        processor._active_service = target_llm


        logger.info(f"Target context before LLMContextFrame: {target_context}")
        logger.info(f"Target context messages: {target_context.get_messages()}")


        # Emit agent switched event
        await self._call_event_handler("on_agent_switched", old_active_agent, target_agent)
        logger.info(f"Handoff completed: now using '{target_agent}'")


    def get_current_context(self) -> LLMContext:
        """Get the currently active agent's context.

        Returns:
            The LLMContext of the currently active agent.
        """
        return self._agent_contexts[self._current_agent]
    
    def set_context_aggregator(self, aggregator):
        """Set the context aggregator reference.
        
        This allows the router to update the aggregator's context when switching agents.
        """
        self._context_aggregator = aggregator
        logger.debug("Context aggregator reference set in router")

    
    def _get_llm_by_name(self, agent_name: str) -> LLMService:
        """Get LLM instance by agent name.

        Args:
            agent_name: Name of the agent whose LLM to retrieve.

        Returns:
            The LLMService instance for the specified agent.
        """
        agent_index = list(self._agent_configs.keys()).index(agent_name)
        return self.llms[agent_index]

    def _set_active_agent(self, agent_name: str):
        """Set the active agent asynchronously (for use during runtime)."""
        self._current_agent = agent_name            
        target_llm = self._get_llm_by_name(agent_name)
        self.strategy.active_service = target_llm

        if hasattr(self, '_pipelines'):
            for pipeline in self._pipelines:
                for processor in pipeline.processors:
                    if isinstance(processor, ServiceSwitcher.ServiceSwitcherFilter):
                        processor._active_service = target_llm


        logger.debug(f"Active agent set to: {agent_name}")

    def _get_agent_by_llm(self, llm: LLMService) -> Optional[str]:
        """Get agent name by LLM instance (reverse lookup).

        This is a helper method that performs a reverse lookup: given an LLM service
        instance, it returns the corresponding agent name. This is useful for debugging
        and logging when you have an LLM instance (like from strategy.active_service)
        and need to know which agent it belongs to.

        Args:
            llm: The LLM service instance to look up.

        Returns:
            The agent name for the specified LLM, or None if not found.
        """
        return self._llm_to_agent.get(llm)


    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames and inject current agent's context into LLMRunFrames.

        Args:
            frame: The frame to process.
            direction: The direction of frame flow.
        """
        # Convert LLMRunFrames to LLMContextFrames with current agent's context
        if isinstance(frame, LLMRunFrame):
            current_context = self._agent_contexts[self._current_agent]
            # Create a new frame with the current context
            # This ensures we always use the latest context state
            context_messages = current_context.get_messages()
            non_system_count = len([m for m in context_messages if m.get("role") != "system"])
            frame = LLMContextFrame(context=current_context)
            logger.debug(
                f"[process_frame] Injected context for '{self._current_agent}' - "
                f"total messages: {len(context_messages)}, non-system: {non_system_count}"
            )
            
            # If we see old messages being restored, log a warning
            if non_system_count > 5:  # Threshold for detecting old conversation
                logger.warning(
                    f"[process_frame] WARNING: Context for '{self._current_agent}' has {non_system_count} non-system messages. "
                    f"This might indicate old messages were restored."
                )

        await super().process_frame(frame, direction)



