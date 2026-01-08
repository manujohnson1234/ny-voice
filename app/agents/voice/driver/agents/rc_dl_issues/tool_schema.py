from typing import List
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema


get_doc_status = FunctionSchema(
    name = "get_doc_status",
    description = "Get the status of the driver's documents (RC/DL)",
    properties = {},
    required = []
)

bot_fail_to_resolve = FunctionSchema(
    name = "bot_fail_to_resolve",
    description = "Bot failed to resolve the issue",
    properties = {},
    required = []
)

def get_rc_dl_issues_tool_schema() -> List[FunctionSchema]:
    return [get_doc_status, bot_fail_to_resolve]