from typing import List, Tuple

from pipecat.services.llm_service import LLMService
from app.agents.voice.driver.agents.not_getting_rides.agent import NotGettingRidesAgent
from app.agents.voice.driver.agents.ride_related_issues.agent import RideIssueAgent
from app.agents.voice.driver.agents.rc_dl_issues.agent import RC_DL_IssuesAgent
from app.agents.voice.driver.agents.router.agent import AgentConfig

def create_agents_list(session_id: str, language: str) -> List[Tuple[LLMService, AgentConfig]]:


    agents_configs: List[Tuple[LLMService, AgentConfig]] = []
    
    not_getting_rides_agent = NotGettingRidesAgent(session_id=session_id, language=language)
    ride_related_issues_agent = RideIssueAgent(session_id=session_id, language=language)
    rc_dl_issues_agent = RC_DL_IssuesAgent(session_id=session_id, language=language)

    config_for_not_getting_rides_agent = AgentConfig(
        agentName="not_getting_rides",
        description="Not getting rides agent",
        system_prompt=not_getting_rides_agent.get_system_prompt(),
        tools=not_getting_rides_agent.get_tools()
    )

    config_for_ride_related_issues_agent = AgentConfig(
        agentName="ride_related_issues",
        description="Ride related issues agent",
        system_prompt=ride_related_issues_agent.get_system_prompt(),
        tools=ride_related_issues_agent.get_tools()
    )

    config_for_rc_dl_issues_agent = AgentConfig(
        agentName="rc_dl_issues",
        description="RC DL issues agent",
        system_prompt=rc_dl_issues_agent.get_system_prompt(),
        tools=rc_dl_issues_agent.get_tools()
    )

    agents_configs.append((not_getting_rides_agent.get_llm(), config_for_not_getting_rides_agent))
    agents_configs.append((ride_related_issues_agent.get_llm(), config_for_ride_related_issues_agent))
    agents_configs.append((rc_dl_issues_agent.get_llm(), config_for_rc_dl_issues_agent))

    return agents_configs