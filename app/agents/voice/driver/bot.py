import argparse
import asyncio
import io
import os
import sys
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional
import aiofiles
import boto3
from zoneinfo import ZoneInfo


project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask,PipelineParams
from pipecat.transports.daily.transport import DailyParams, DailyTransport


from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMContext


from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor, RTVIObserver
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame, LLMMessagesUpdateFrame
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.transcriptions.language import Language
from pipecat.frames.frames import FilterEnableFrame, CancelFrame, LLMContextFrame

from pipecat.audio.filters.koala_filter import KoalaFilter
from pipecat.audio.filters.aic_filter import AICFilter

from pipecat.frames.frames import FilterEnableFrame
from pipecat.audio.vad.silero import SileroVADAnalyzer

from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from pipecat.frames.frames import TTSSpeakFrame

from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor

from pipecat.utils.tracing.conversation_context_provider import (
    ConversationContextProvider,
)

from loguru import logger

from app.agents.voice.driver.tts import get_tts_service
from app.agents.voice.driver.stt import get_stt_service
from app.agents.voice.driver.llm import get_llm_service


from app.agents.voice.driver.utils.handover import HandoverFrame

from app.agents.voice.driver.utils.bot_words import get_bot_words
from app.core import config
from app.core.session_manager import get_session_manager
from app.core.session_manager import SessionManager

from app.agents.voice.driver.agents.router.agent import AgentRouter
from app.agents.voice.driver.utils.utils import create_agents_list

from app.agents.voice.driver.analytics.tracing_setup import setup_tracing
from langfuse import get_client
from opentelemetry import trace

load_dotenv(override=True)




def upload_to_s3_from_memory(audio_data: bytes, bucket_name: str, object_key: str):
    """Upload audio data directly from memory to S3 using boto3."""
    s3 = boto3.client('s3', region_name=config.AWS_REGION)
    with io.BytesIO(audio_data) as buffer:
        buffer.seek(0)  # Reset buffer position to start
        s3.upload_fileobj(buffer, bucket_name, object_key)
    logger.info(f"Audio uploaded successfully to s3://{bucket_name}/{object_key}")


async def save_audio_file(audio: bytes, filename: str, sample_rate: int, num_channels: int):
    """Save audio data to a WAV file locally and optionally to S3. Both operations are independent."""
    if len(audio) > 0 :
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wf:
                wf.setsampwidth(2)
                wf.setnchannels(num_channels)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)
            audio_data = buffer.getvalue()
            
            # Save to local file (independent operation)
            if config.ENABLE_LOCAL_STORAGE:
                try:
                    async with aiofiles.open(filename, "wb") as file:
                        await file.write(audio_data)
                    logger.info(f"Audio saved to {filename}")
                except Exception as e:
                    logger.error(f"Failed to save audio to local file: {e}")

            
            # Upload to S3 if enabled (independent operation - doesn't depend on local file)
            if config.ENABLE_S3_STORAGE:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    object_key = filename
                    
                    # Upload to S3 directly from memory buffer (independent from local save)
                    await asyncio.to_thread(
                        upload_to_s3_from_memory,
                        audio_data,
                        config.S3_BUCKET_NAME,
                        object_key
                    )
                except Exception as e:
                    logger.error(f"Failed to upload audio to S3: {e}")



async def run_bot(room_url: str, token: str, session_id: str, language_code: str, agent_name: str):
    # Initialize session manager
    driver_number = "8610263112"
    current_version_of_app = ""
    latest_version_of_app = ""
    ride_id = None


    session_manager = get_session_manager()
    
    # Create session with initial data
    initial_data = {
        "switch_count" : 0,
        "count_tool_calls": {}
    }
    
    
    await session_manager.create_session(
        session_id=session_id,
        initial_data=initial_data
    )
    logger.info(f"Session {session_id} initialized ")

    
    stt = get_stt_service(language=language_code) # for malayalam use sarvam 

    tts = get_tts_service(language=language_code) 


    agents = create_agents_list(session_id=session_id, language=language_code)


    llms = AgentRouter(agents=agents, initial_agent=agent_name, session_id=session_id)


    system_prompt = llms.get_current_context()  
    tools = llms.get_current_tools()
    context = LLMContext(messages=system_prompt, tools=tools)
    context_aggregator = LLMContextAggregatorPair(context)
    
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    daily_params = DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(confidence=0.3,
        start_secs=0.2,
        stop_secs=0.7,)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(),
    )


    if (config.ENABLE_KOALA_FILTER):
        daily_params.audio_in_filter = KoalaFilter(access_key=config.KOALA_ACCESS_KEY)
    elif (config.ENABLE_AIC_FILTER):
        daily_params.audio_in_filter  = AICFilter(license_key=config.AIC_ACCESS_KEY,enhancement_level=1.0)

    setup_tracing(service_name="ny-driver-bot")


    transport = DailyTransport(
        room_url,
        token,
        "Namma Yatri Voice Agent",
        daily_params,
    )


    # Create STT debug processor
    # stt_debug = STTDebugProcessor()

    audiobuffer = AudioBufferProcessor()

    handoverFrame = HandoverFrame(session_id, session_manager)
    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,  # RTVI processor
            stt,
            # stt_debug,  # STT output for debugging
            context_aggregator.user(),  # User responses
            llms,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            audiobuffer,
            handoverFrame,
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )
    # ist_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    # timestamp = ist_time.strftime("%Y-%m-%d_%H-%M-%S")
    # conversation_id = f"{driver_number}-{session_id}-{timestamp}"


    task_params ={
        "params": PipelineParams(allow_interruptions=True),
        "cancel_on_idle_timeout": True,
        "observers": [RTVIObserver(rtvi)],
    }

    # if config.ENABLE_TRACING:
    #     task_params["conversation_id"] = conversation_id
    #     task_params["enable_tracing"] = True

    task = PipelineTask(pipeline, **task_params)


    # Timer task variable to store the background timer
    timer_task = None

    # Timer callback function
    async def on_timer_expired(session_id: str, task: PipelineTask):
        """Callback function called when the 3-minute timer expires."""
        logger.info(f"3-minute timer expired for session {session_id}")
        await session_manager.set_value(session_id, "bot_not_able_to_resolve", "true")
        await session_manager.set_value(session_id, "reason", "time_out_error")

        # Additional actions can be added here
    

    @task.event_handler("on_pipeline_error")
    async def on_pipeline_error(task, frame):
        print("Pipeline error:", frame.error)
        
    @handoverFrame.event_handler("on_end_call")
    async def on_end_call(handoverFrame):
        logger.info("End call")
        await session_manager.delete_session(session_id)
        await task.cancel()


    @handoverFrame.event_handler("on_bot_fail_to_resolve")
    async def on_bot_fail_to_resolve(handoverFrame):
        logger.info("Bot failed to resolve")
        sentence = await session_manager.get_value(session_id, "reason")
        message = get_bot_words(language=language_code, key=sentence)
        await task.queue_frames([TTSSpeakFrame(message)])
        await task.queue_frames([RTVIServerMessageFrame(data={"event": "on_bot_fail_to_resolve"})])
        await session_manager.set_value(session_id, "end_call", "true")


    @rtvi.event_handler("on_client_message")
    async def on_client_message(rtvi, msg):
        logger.info(f"RTVI client message - type: {msg.type}, data: {msg.data}")


        if msg.type == "initial_data":
            data = msg.data
            phone_number = data.get("phone_number")
            agent_name = data.get("agent_name")
            ride_id = data.get("ride_id")
            current_version_of_app = data.get("current_version_of_app")
            latest_version_of_app = data.get("latest_version_of_app")
            
            if phone_number:
                await session_manager.set_value(session_id, "driver_number", phone_number)
            if ride_id:
                await session_manager.set_value(session_id, "ride_id", ride_id)
            if current_version_of_app:
                await session_manager.set_value(session_id, "current_version_of_app", current_version_of_app)
            if latest_version_of_app:
                await session_manager.set_value(session_id, "latest_version_of_app", latest_version_of_app)

            llm_context = llms.get_current_context()
            llm_router_message = "when the driver has issue about their rides or fare, use the tool change_agent with the parameter agent_name='ride_related_issues' ."
            
            # Add llm_router_message to the beginning of the first message's content
            if llm_context and len(llm_context) > 0 and "content" in llm_context[0]:
                llm_context[0]["content"] = llm_router_message + "\n\n" + llm_context[0]["content"]
            
            first_message = f"switch to agent {agent_name}"
            llm_context.append({"role": "system", "content": first_message})


            await task.queue_frames([
                LLMMessagesUpdateFrame(llm_context),
                LLMRunFrame() 
            ])
            
    @transport.event_handler("on_joined")
    async def on_joined(transport, participant):
        await task.queue_frame(FilterEnableFrame(True))


    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        nonlocal timer_task
        logger.info("Client connected")

        await task.queue_frames([RTVIServerMessageFrame(data={"event": "bro_give_me_the_initial_data"})])
        # Update session with connection info
        await session_manager.set_value(session_id, "connected_at", datetime.now().isoformat())
        await session_manager.set_value(session_id, "status", "connected")
        
        # Example: Retrieve session data
        session_data = await session_manager.get_session(session_id)
        logger.info(f"Session data: {session_data}")

        await audiobuffer.start_recording()
    

        # Start 3-minute timer
        async def timer_function():
            await asyncio.sleep(190)  # 3 minutes
            await on_timer_expired(session_id, task)

        timer_task = asyncio.create_task(timer_function())
        logger.info(f"Started 3-minute timer for session {session_id}")


    
    @audiobuffer.event_handler("on_audio_data")
    async def in_audio_data(buffer, audio, sample_rate, num_channels):
        if config.ENABLE_RECORDING:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recordings/{driver_number}_{timestamp}.wav"
            if config.ENABLE_LOCAL_STORAGE:
                os.makedirs("recordings", exist_ok=True)
            await save_audio_file(audio, filename, sample_rate, num_channels)
        else:
            logger.info("Audio recording is disabled")


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
        
        await task.cancel()


    
        

    @llms.event_handler("on_agent_switched")
    async def on_agent_switched(llms):
        new_context = llms.get_current_context() 

        current_agent_name = llms.get_current_agent_name()

        if current_agent_name == "router":
            llm_router_message = "when the driver has issue about their rides or fare. ask them to end the call and select the ride from the app which they have issue."
            if llm_context and len(llm_context) > 0 and "content" in llm_context[0]:
                llm_context[0]["content"] = llm_router_message + "\n\n" + llm_context[0]["content"]
        


        switch_count = await session_manager.get_value(session_id, "switch_count")
        if switch_count >= 1:
            old_messages = context.get_messages()
            for msg in reversed(old_messages):
                if msg.get("role") == "user":
                    new_context.append({
                        "role": "user",
                        "content": msg.get("content", "")
                    })
                    break
        switch_count = switch_count + 1
        await session_manager.set_value(session_id, "switch_count", switch_count)


        await task.queue_frames([
            LLMMessagesUpdateFrame(new_context),
            LLMRunFrame() 
        ])

    runner = PipelineRunner()

    async def run_pipeline():
        try:
            await runner.run(task)
        except asyncio.CancelledError:
            logger.info("Main task cancelled. Exiting gracefully.")
        except Exception as e:
            logger.error(f"Pipeline runner error: {e}")

    

    if config.ENABLE_TRACING:
        # langfuse_client = get_client()
        # tracer = trace.get_tracer(__name__)
        # with tracer.start_as_current_span(conversation_id) as root_span:
        #     logger.info(
        #         f"Starting current span with conversation ID: {conversation_id}"
        #     )
        #     root_span.set_attribute("driver_number", driver_number)
        #     root_span.set_attribute("language_code", language_code)
        #     root_span.set_attribute("current_version_of_app", current_version_of_app)
        #     root_span.set_attribute("latest_version_of_app", latest_version_of_app)
        #     root_span.set_attribute("session_id", session_id)
            


        #     langfuse_client.update_current_trace(
        #         user_id=driver_number,
        #         session_id=session_id
        #     )

        #     provider = ConversationContextProvider.get_instance()
        #     provider.set_current_conversation_context(
        #         root_span.get_span_context(), conversation_id
        #     )
        #     logger.info(
        #         f"Set Pipecat conversation context with span ID: {root_span.get_span_context().span_id}"
        #     )
            await run_pipeline()
    else:
        await run_pipeline()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the daily room"
    )
    parser.add_argument("-t", "--token", type=str, required=True, help="daily token")
    parser.add_argument(
        "--session-id", type=str, required=True, help="Session ID for logging"
    )

    parser.add_argument("--language-code", type=str, required=True, help="Language code")

    parser.add_argument("--agent-name", type=str, required=True, help="Agent name")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_bot(args.url, args.token, args.session_id, args.language_code, args.agent_name))
