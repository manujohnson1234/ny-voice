from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import BotStoppedSpeakingFrame

from app.core.session_manager import get_session_manager
from app.core.session_manager import SessionManager

class HandoverFrame(FrameProcessor):
    def __init__(self, session_id: str, session_manager: SessionManager):
        super().__init__()
        self.session_id = session_id
        self.session_manager = session_manager
        self._register_event_handler("on_bot_fail_to_resolve")
        self._register_event_handler("on_end_call")


    

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        bot_not_able_to_resolve = await self.session_manager.get_value(self.session_id, "bot_not_able_to_resolve")
        if bot_not_able_to_resolve == "true":
            await self.session_manager.set_value(self.session_id, "bot_not_able_to_resolve", "false")
            await self._call_event_handler("on_bot_fail_to_resolve")
            return

        if isinstance(frame, BotStoppedSpeakingFrame):
            end_call = await self.session_manager.get_value(self.session_id, "end_call")
            if end_call == "true":
                await self._call_event_handler("on_end_call")
                return

        await self.push_frame(frame, direction)