from pipecat.frames.frames import (
    LLMMessagesAppendFrame
)

class IdleHandler:
    def __init__(self):
        self._retry_count = 0
    
    async def handle_idle(self, aggregator):
        self._retry_count += 1

        if self._retry_count > 2:
            message = {
                "role": "system",
                "content": "use the tool bot_fail_to_resolve",
            }
            await aggregator.push_frame(LLMMessagesAppendFrame([message], run_llm=True))
            return
        
        message = {
            "role": "system",
            "content": "The user has been quiet. Politely and briefly ask if they're still there.",
        }
        await aggregator.push_frame(LLMMessagesAppendFrame([message], run_llm=True))
    
    def reset(self):
        self._retry_count = 0