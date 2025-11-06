from pipecat.adapters.schemas.function_schema import FunctionSchema

driver_info = FunctionSchema(
    name="get_driver_info",
    description="Retrieve driver information of Namma Yatri",
    properties={},
    required=[]
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