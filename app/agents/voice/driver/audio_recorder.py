import asyncio
import wave
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
from pipecat.frames.frames import AudioRawFrame, Frame
from pipecat.processors.frame_processor import FrameProcessor


class AudioRecorderProcessor(FrameProcessor):
    """
    A processor that records incoming audio frames to a WAV file.
    """
    
    def __init__(
        self,
        output_dir: str = "recordings",
        session_id: str = None,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,  # 2 bytes = 16-bit
        **kwargs
    ):
        super().__init__(**kwargs)
        self._output_dir = Path(output_dir)
        self._session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        
        # Create output directory if it doesn't exist
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp and session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._filename = self._output_dir / f"audio_input_{self._session_id}_{timestamp}.wav"
        
        self._wav_file = None
        self._is_recording = False
        self._audio_buffer = []
        
        logger.info(f"AudioRecorderProcessor initialized. Will save to: {self._filename}")
    
    async def process_frame(self, frame: Frame, direction):
        """Process each frame passing through the pipeline."""
        await super().process_frame(frame, direction)
        
        # Check if this is an audio frame
        if isinstance(frame, AudioRawFrame):
            await self._save_audio_frame(frame)
        
        # Always pass the frame to the next processor
        await self.push_frame(frame, direction)
    
    async def _save_audio_frame(self, frame: AudioRawFrame):
        """Save the audio frame data to the WAV file."""
        try:
            if not self._is_recording:
                self._start_recording()
            
            # Write the audio data to the WAV file
            if self._wav_file and frame.audio:
                self._wav_file.writeframes(frame.audio)
                
        except Exception as e:
            logger.error(f"Error saving audio frame: {e}")
    
    def _start_recording(self):
        """Initialize the WAV file for recording."""
        try:
            self._wav_file = wave.open(str(self._filename), 'wb')
            self._wav_file.setnchannels(self._channels)
            self._wav_file.setsampwidth(self._sample_width)
            self._wav_file.setframerate(self._sample_rate)
            self._is_recording = True
            logger.info(f"Started recording audio to {self._filename}")
        except Exception as e:
            logger.error(f"Error starting audio recording: {e}")
            self._is_recording = False
    
    def stop_recording(self):
        """Stop recording and close the WAV file."""
        if self._wav_file:
            try:
                self._wav_file.close()
                self._is_recording = False
                logger.info(f"Stopped recording. Audio saved to {self._filename}")
            except Exception as e:
                logger.error(f"Error stopping audio recording: {e}")
    
    async def cleanup(self):
        """Cleanup method called when the processor is being shut down."""
        await asyncio.sleep(0)  # Make this properly async
        self.stop_recording()
        await super().cleanup()

