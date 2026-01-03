from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

get_ride_details = FunctionSchema(
    name = "get_ride_details",
    description = "Get the ride details like distance, fare, toll charges, etc.",
    properties = {
        "issue": {
            "type": "string",
            "description": "The issue with the ride",
            "enum": ["TOLL_CHARGES", "FARE"]
        }
    },
    required = ["issue"]
)

bot_fail_to_resolve = FunctionSchema(
    name = "bot_fail_to_resolve",
    description = "Escalate the call to Namma Yatri support team when the bot cannot resolve the issue",
    properties = {},
    required = []
)

def get_ride_related_issues_tool_schema():
    return ToolsSchema(standard_tools=[get_ride_details, bot_fail_to_resolve])

