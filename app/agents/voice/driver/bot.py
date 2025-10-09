import argparse
import asyncio
import os
from dotenv import load_dotenv
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask,PipelineParams
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor, RTVIObserver
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.services.google.tts import GoogleTTSService
from pipecat.transcriptions.language import Language
from pipecat.services.google.stt import GoogleSTTService
from pipecat.frames.frames import FilterEnableFrame, CancelFrame
from pipecat.audio.filters.koala_filter import KoalaFilter
from pipecat.runner.livekit import configure
from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport
from pipecat.services.openai.stt import OpenAISTTService


from google.cloud.speech_v1 import RecognitionConfig

from loguru import logger

from tool_schema import driver_info, send_dummy_request
from system_prompt import not_getting_rides_system_prompt
from function_handler import get_driver_info_handler, send_dummy_notification_handler
# from stt_debug import STTDebugProcessor
# from audio_recorder import AudioRecorderProcessor



import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core import config


load_dotenv(override=True)


async def run_bot(room_url: str, token: str, session_id: str, driver_number: str):
    # stt = DeepgramSTTService(api_key=DEEPGRAM_API_KEY)

    # (url, token, room_name) = await configure()

    # stt = GoogleSTTService(
    #     params=GoogleSTTService.InputParams(
    #         languages=Language.TA_IN,
    #         enable_automatic_punctuation=False 
    #         ),
    #     credentials=os.getenv("GOOGLE_TEST_CREDENTIALS"),
    # )

    # tts = CartesiaTTSService(
    #     api_key=CARTESIA_API_KEY,
    #     voice_id="56e35e2d-6eb6-4226-ab8b-9776515a7094",
    # )
    stt = OpenAISTTService(
        api_key=config.OPENAI_API_KEY,
        model="gpt-4o-transcribe",
        language = Language.HI_IN,
    )

    tts = GoogleTTSService(
        voice_id="hi-IN-Chirp3-HD-Autonoe",
        params=GoogleTTSService.InputParams(language=Language.HI_IN),
        credentials=os.getenv("GOOGLE_TEST_CREDENTIALS"),
        interim_results=True, 
    )

    llm = OpenAILLMService(api_key=config.OPENAI_API_KEY)


    tools = ToolsSchema(standard_tools=[driver_info,send_dummy_request])

    messages = not_getting_rides_system_prompt

    context = OpenAILLMContext(messages, tools=tools)
    context_aggregator = llm.create_context_aggregator(context)


    # Register function handlers
    llm.register_function("get_driver_info", get_driver_info_handler)
    llm.register_function("send_dummy_request", send_dummy_notification_handler)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Create audio recorder to save incoming audio
    # audio_recorder = AudioRecorderProcessor(
    #     output_dir="recordings",
    #     session_id=session_id,
    #     sample_rate=16000,  # Match your audio configuration
    #     channels=1,
    #     sample_width=2
    # )

    # @llm.event_handler("on_function_calls_started")
    # async def on_function_calls_started(llm, function_calls):

    # livekitParams = LiveKitParams(
    #             audio_in_enabled=True,
    #             audio_out_enabled=True,
    #             vad_analyzer=SileroVADAnalyzer(params=VADParams(confidence=0.5,
    #     start_secs=0.1,
    #     stop_secs=0.1,)),  # Use default
    #             turn_analyzer=LocalSmartTurnAnalyzerV3(),
    #         )

    daily_params = DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        # audio_in_filter=KoalaFilter(access_key=config.KOALA_ACCESS_KEY),
        vad_analyzer=SileroVADAnalyzer(params=VADParams(confidence=0.3,
        start_secs=0.2,
        stop_secs=0.7,)),
        # vad_analyzer=None,
        turn_analyzer=LocalSmartTurnAnalyzerV3(),
    )

    transport = DailyTransport(
        room_url,
        token,
        "Namma Yatri Voice Agent",
        daily_params,
    )


    # transport = LiveKitTransport(
    #     room_url,
    #     token,
    #     "Namma Yatri Voice Agent",
    #     livekitParams,
    # )

    # Create STT debug processor
    # stt_debug = STTDebugProcessor()

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            # audio_recorder,  # Record incoming audio for debugging
            rtvi,  # RTVI processor
            stt,
            # stt_debug,  # STT output for debugging
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        # Stop and save the audio recording
        # audio_recorder.stop_recording() 
        await task.cancel()

    @transport.event_handler("on_user_started_speaking")
    async def on_user_started_speaking(transport):
        logger.info("User started speaking - cancelling current bot operation")
        # Cancel any ongoing LLM/TTS operations when user interrupts
        await task.queue_frames([CancelFrame()])

    runner = PipelineRunner()
    await runner.run(task)

    await task.queue_frame(FilterEnableFrame(True))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the livekit room"
    )
    parser.add_argument("-t", "--token", type=str, required=True, help="Livekit token")
    parser.add_argument(
        "--session-id", type=str, required=True, help="Session ID for logging"
    )
    parser.add_argument("--driver-number", type=str, required=True, help="Driver number")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_bot(args.url, args.token, args.session_id, args.driver_number))