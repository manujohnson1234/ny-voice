from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

driver_info = FunctionSchema(
    name="get_driver_info",
    description="Retrieve driver information of Namma Yatri",
    properties={
        "time_till_not_getting_rides": {
            "type": "integer",
            "description": "Time till not getting rides in minutes"
        },
        "time_quantity": {
            "type": "string",
            "description": "Time quantity in minutes or hours",
            "enum": ["MINUTE", "HOUR"]
        },
    },
    required=[],
)

send_dummy_request = FunctionSchema(
    name="send_dummy_request", 
    description="Send dummy ride request notification to a driver for testing App is working properly",
    properties={},
    required=[]
)

send_overlay_sms = FunctionSchema(
    name="send_overlay_sms",
    description="Send overlay SMS to a driver for dues payment",
    properties={},
    required=[]
)

bot_fail_to_resolve = FunctionSchema(
    name="bot_fail_to_resolve",
    description="Bot failed to resolve the issue",
    properties={},
    required=[]
)

def get_not_getting_rides_tool_schema():
    return ToolsSchema(standard_tools=[driver_info, send_dummy_request, send_overlay_sms, bot_fail_to_resolve])