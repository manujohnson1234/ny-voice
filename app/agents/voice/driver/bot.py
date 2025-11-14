import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path


project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask,PipelineParams
from pipecat.transports.services.daily import DailyParams, DailyTransport


from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair


from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor, RTVIObserver
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.transcriptions.language import Language
from pipecat.frames.frames import FilterEnableFrame, CancelFrame, LLMContextFrame

from pipecat.audio.filters.koala_filter import KoalaFilter
from pipecat.frames.frames import FilterEnableFrame
from pipecat.audio.vad.silero import SileroVADAnalyzer

from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from pipecat.frames.frames import TTSSpeakFrame

from loguru import logger

from app.agents.voice.driver.tts import get_tts_service
from app.agents.voice.driver.stt import get_stt_service
from app.agents.voice.driver.llm import get_llm_service

from app.agents.voice.driver.not_getting_rides.tool_schema import driver_info, send_dummy_request, send_overlay_sms,bot_fail_to_resolve
from app.agents.voice.driver.not_getting_rides.system_prompt import get_not_getting_rides_system_prompt
from app.agents.voice.driver.not_getting_rides.function_handler import get_driver_info_handler, send_dummy_notification_handler, send_overlay_sms_handler,bot_fail_to_resolve_handler

from app.agents.voice.driver.utils.handover import HandoverFrame

from app.agents.voice.driver.utils.bot_words import get_bot_words
from app.core import config
from app.core.session_manager import get_session_manager
from app.core.session_manager import SessionManager



load_dotenv(override=True)


async def run_bot(room_url: str, token: str, session_id: str, driver_number: str):
    # Initialize session manager
    session_manager = get_session_manager()
    
    # Create session with initial data
    await session_manager.create_session(
        session_id=session_id,
        initial_data={
            "driver_number": driver_number,
            "count_tool_calls": {}
        }
    )
    logger.info(f"Session {session_id} initialized for driver {driver_number}")

    language = "hi" 
    
    stt = get_stt_service(language=language) # for malayalam use sarvam 

    tts = get_tts_service(language=language) 

    agent_for_not_getting_rides = get_llm_service()


    tools = ToolsSchema(standard_tools=[driver_info,send_dummy_request,send_overlay_sms,bot_fail_to_resolve])

    messages = get_not_getting_rides_system_prompt(language=language)
    
    

    context = OpenAILLMContext(messages, tools=tools)
    context_aggregator = agent_for_not_getting_rides.create_context_aggregator(context)


    # Register function handlers with session_id captured in closure
    # Create wrapper functions that have access to session_id
    async def get_driver_info_wrapper(params):
        return await get_driver_info_handler(params, session_id=session_id)
    
    async def send_dummy_notification_wrapper(params):
        return await send_dummy_notification_handler(params, session_id=session_id)
    
    async def send_overlay_sms_wrapper(params):
        return await send_overlay_sms_handler(params, session_id=session_id)
    
    async def bot_fail_to_resolve_wrapper(params):
        return await bot_fail_to_resolve_handler(params, session_id=session_id)

    agent_for_not_getting_rides.register_function("get_driver_info", get_driver_info_wrapper)
    agent_for_not_getting_rides.register_function("send_dummy_request", send_dummy_notification_wrapper)
    agent_for_not_getting_rides.register_function("send_overlay_sms", send_overlay_sms_wrapper)
    agent_for_not_getting_rides.register_function("bot_fail_to_resolve", bot_fail_to_resolve_wrapper)


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



    daily_params = DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(confidence=0.3,
        start_secs=0.2,
        stop_secs=0.7,)),
        # vad_analyzer=None,
        turn_analyzer=LocalSmartTurnAnalyzerV3(),
    )


    if (config.ENABLE_KOALA_FILTER):
        daily_params.audio_in_filter = KoalaFilter(access_key=config.KOALA_ACCESS_KEY)
    elif (config.ENABLE_AIC_FILTER):
        daily_params.audio_in_filter  = AICFilter(license_key=config.AIC_ACCESS_KEY)




    transport = DailyTransport(
        room_url,
        token,
        "Namma Yatri Voice Agent",
        daily_params,
    )


    # Create STT debug processor
    # stt_debug = STTDebugProcessor()

    # completionListener = CompletionListener(session_id, session_manager)
    handoverFrame = HandoverFrame(session_id, session_manager)
    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            # audio_recorder,  # Record incoming audio for debugging
            rtvi,  # RTVI processor
            stt,
            # stt_debug,  # STT output for debugging
            context_aggregator.user(),  # User responses
            agent_for_not_getting_rides,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            handoverFrame,
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

    # Timer task variable to store the background timer
    timer_task = None

    # Timer callback function
    async def on_timer_expired(session_id: str, task: PipelineTask):
        """Callback function called when the 3-minute timer expires."""
        logger.info(f"3-minute timer expired for session {session_id}")
        await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
        await session_manager.set_value(session_id, "reason", "time_out_error")

        # Additional actions can be added here
    
    
    @handoverFrame.event_handler("on_end_call")
    async def on_end_call(handoverFrame):
        logger.info("End call")
        await session_manager.delete_session(session_id)
        await task.queue_frames([CancelFrame()])
        await task.cancel()


    @handoverFrame.event_handler("on_bot_fail_to_resolve")
    async def on_bot_fail_to_resolve(handoverFrame):
        logger.info("Bot failed to resolve")
        sentence = await session_manager.get_value(session_id, "reason")
        message = get_bot_words(language=language, key=sentence)
        logger.info(f"Bot words: {message}")
        await task.queue_frames([TTSSpeakFrame(message)])
        await task.queue_frames([RTVIServerMessageFrame(data={"event": "on_bot_fail_to_resolve"})])
        await session_manager.set_value(session_id, "end_call", "true")



    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        nonlocal timer_task
        logger.info("Client connected")
        
        # Update session with connection info
        await session_manager.set_value(session_id, "connected_at", datetime.now().isoformat())
        await session_manager.set_value(session_id, "status", "connected")
        
        # Example: Retrieve session data
        session_data = await session_manager.get_session(session_id)
        logger.info(f"Session data: {session_data}")
    
        await task.queue_frames([LLMRunFrame()])

        # Start 3-minute timer
        async def timer_function():
            await asyncio.sleep(190)  # 3 minutes
            await on_timer_expired(session_id, task)

        timer_task = asyncio.create_task(timer_function())
        logger.info(f"Started 3-minute timer for session {session_id}")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        nonlocal timer_task
        logger.info("Client disconnected")
        
        # Update session with disconnection info
        await session_manager.set_value(session_id, "disconnected_at", datetime.now().isoformat())
        await session_manager.set_value(session_id, "status", "disconnected")
        
        # Example: Retrieve final session data before cleanup
        final_session_data = await session_manager.get_session(session_id)
        logger.info(f"Final session data: {final_session_data}")
    
        # Cancel timer if it's still running
        if timer_task and not timer_task.done():
            timer_task.cancel()
            try:
                await timer_task
            except asyncio.CancelledError:
                logger.info(f"Timer cancelled for session {session_id}")
        
        # Stop and save the audio recording
        # audio_recorder.stop_recording() 
        await task.cancel()

    runner = PipelineRunner()
    await runner.run(task)

    @transport.event_handler("on_joined")
    async def on_joined(transport):
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