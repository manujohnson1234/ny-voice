from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import Frame, TranscriptionFrame, InterimTranscriptionFrame
from loguru import logger


class STTDebugProcessor(FrameProcessor):
    """Debugging processor to monitor STT output flowing to LLM"""
    
    async def process_frame(self, frame: Frame, direction):
        await super().process_frame(frame, direction)
        
        # Log interim (partial) transcriptions
        if isinstance(frame, InterimTranscriptionFrame):
            logger.debug(f"🔵 [STT PARTIAL] {frame.text}")
            print(f"🔵 [STT PARTIAL] {frame.text}")
        
        # Log final transcriptions
        elif isinstance(frame, TranscriptionFrame):
            logger.info(f"🟢 [STT FINAL] {frame.text}")
            print(f"🟢 [STT FINAL] {frame.text}")
        
        # Pass the frame along the pipeline
        await self.push_frame(frame, direction)

