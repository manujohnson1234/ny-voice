from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.llm_service import LLMService
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

from ..router_class.agent_router import AgentConfig


@dataclass
class CreateAgentConfig:
    name: str
    description: str
    system_prompt: str
    tools: Optional[ToolsSchema] = None
    functions: Optional[List[Tuple[str, Callable]]] = None


class CreateAgent:
    """Builder class for creating multiple agents with shared configuration.
    
    This class simplifies the creation of multiple agents that share the same
    API key outputting a dictionary ready for AgentRouter.
    
    Example:
        agent_builder = CreateAgent(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        agents = agent_builder.build_agents([
            CreateAgentConfig(
                name="router",
                description="Routes questions",
                system_prompt="You route users.",
                tools=None
            ),
            CreateAgentConfig(
                name="movie_agent",
                description="Movie expert",
                system_prompt="You are a movie expert.",
                tools=movie_tools
            )
        ])
        
        router = AgentRouter(agents=agents, initial_agent="router")
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialize the CreateAgent builder.
        
        Args:
            api_key: OpenAI API key to use for all agents
        """
        self.api_key = api_key
        self.model = model
    
    def build_agents(
        self, configs: List[CreateAgentConfig]
    ) -> Dict[str, Tuple[LLMService, AgentConfig]]:
        """Build agents from configurations.
        
        Args:
            configs: List of agent configurations
            
        Returns:
            Dictionary mapping agent names to (LLMService, AgentConfig) tuples,
            ready to be passed to AgentRouter
        """
        agents = {}
        
        for config in configs:
            # Create LLM instance with shared api_key
            llm = OpenAILLMService(
                api_key=self.api_key,
                model=self.model
            )
            
            # Register function handlers if provided
            if config.functions:
                from loguru import logger
                logger.info(f"Registering {len(config.functions)} functions for agent '{config.name}'")
                for (function_name, function_handler) in config.functions:
                    logger.info(f"  - Registering function: {function_name}")
                    llm.register_function(function_name, function_handler)


            # Convert CreateAgentConfig to AgentConfig
            agent_config = AgentConfig(
                name=config.name,
                description=config.description,
                system_prompt=config.system_prompt,
                tools=config.tools
            )
            
            # Add to agents dictionary
            agents[config.name] = (llm, agent_config)
        
        return agents