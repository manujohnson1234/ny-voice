from typing import List
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

change_agent = FunctionSchema(
    name = "change_agent",
    description = "Change the agent to the next agent",
    properties = {
        "agent_name": {
            "type": "string",
            "description": "The agent to change to",
        }
    },
    required = ["agent_name"]
)

def get_router_tool_schema() -> List[FunctionSchema]:
    return [change_agent]