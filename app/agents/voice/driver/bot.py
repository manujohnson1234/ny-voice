import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path FIRST before any local imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

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
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

from pipecat.adapters.schemas.function_schema import FunctionSchema

from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor, RTVIObserver
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.services.google.tts import GoogleTTSService
from pipecat.transcriptions.language import Language
from pipecat.services.google.stt import GoogleSTTService
from pipecat.frames.frames import FilterEnableFrame, CancelFrame, LLMContextFrame, LLMMessagesUpdateFrame
from pipecat.audio.filters.koala_filter import KoalaFilter
from pipecat.runner.livekit import configure
from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport
from pipecat.services.openai.stt import OpenAISTTService



from google.cloud.speech_v1 import RecognitionConfig

from loguru import logger

# from app.agents.voice.driver.router_agent.system_prompt import router_agent_system_prompt

from app.agents.voice.driver.not_getting_rides.tool_schema import driver_info, send_dummy_request, send_overlay_sms
from app.agents.voice.driver.not_getting_rides.system_prompt import not_getting_rides_system_prompt
from app.agents.voice.driver.not_getting_rides.function_handler import get_driver_info_handler, send_dummy_notification_handler, send_overlay_sms_handler
# from stt_debug import STTDebugProcessor
# from audio_recorder import AudioRecorderProcessor

# from app.agents.voice.driver.movies.tool_schema import search_movies, get_movie_details
# from app.agents.voice.driver.movies.system_prompt import movies_system_prompt
# from app.agents.voice.driver.movies.function_handler import search_movies_handler, get_movie_details_handler

# from app.agents.voice.driver.create_agent.create_agent import CreateAgent, CreateAgentConfig
# from app.agents.voice.driver.router_class.agent_router import AgentRouter, AgentConfig
from app.core import config
from app.core.session_manager import get_session_manager


load_dotenv(override=True)


async def run_bot(room_url: str, token: str, session_id: str, driver_number: str):
    # Initialize session manager
    session_manager = get_session_manager()
    
    # Create session with initial data
    await session_manager.create_session(
        session_id=session_id,
        initial_data={
            "driver_number": driver_number,
            "conversation_count": 0
        }
    )
    logger.info(f"Session {session_id} initialized for driver {driver_number}")

    # (url, token, room_name) = await configure()

    stt = OpenAISTTService(
        api_key=config.OPENAI_API_KEY,
        model="gpt-4o-transcribe",
        language = Language.HI_IN, # KN_IN
    )

    tts = GoogleTTSService(
        voice_id="hi-IN-Chirp3-HD-Autonoe",  # kn-IN-Chirp3-HD-Autonoe
        params=GoogleTTSService.InputParams(language=Language.HI_IN), # KN_IN
        credentials=os.getenv("GOOGLE_TEST_CREDENTIALS"),
        interim_results=True, 
    )


    # creating agents
    # router_llm = OpenAILLMService(
    #     api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o"
    # )

    # not_getting_rides_llm = OpenAILLMService(
    #     api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o"
    # )

    # not_getting_rides_llm.register_function("get_driver_info", get_driver_info_handler)
    # not_getting_rides_llm.register_function("send_dummy_request", send_dummy_notification_handler)
    # not_getting_rides_llm.register_function("send_overlay_sms", send_overlay_sms_handler)


    # moive_agent = OpenAILLMService(
    #     api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o"
    # )
    # moive_agent.register_function("search_movies", search_movies_handler)
    # moive_agent.register_function("get_movie_details", get_movie_details_handler)

    

    # agent_builder = CreateAgent(api_key=config.OPENAI_API_KEY, model="gpt-4o")

    # agents = agent_builder.build_agents([
    #     CreateAgentConfig(
    #         name="router",
    #         description="Router agent",
    #         system_prompt="You are a router agent. You route the conversation to the appropriate agent.",
    #         tools=None,
    #         functions=None
    #     ),
    #     CreateAgentConfig(
    #         name="not_getting_rides",
    #         description="Agent for not getting rides",
    #         system_prompt=not_getting_rides_system_prompt[0]["content"],
    #         tools=ToolsSchema(standard_tools=[driver_info,send_dummy_request,send_overlay_sms]),
    #         functions=[("get_driver_info", get_driver_info_handler), ("send_dummy_request", send_dummy_notification_handler), ("send_overlay_sms", send_overlay_sms_handler)]
    #     )
    # ])

    # router_config = AgentConfig(
    #     name="router",
    #     description="Router agent",
    #     system_prompt=router_agent_system_prompt[0]["content"],
    #     tools=None
    # )

    # not_getting_rides_config = AgentConfig(
    #     name="not_getting_rides",
    #     description="Agent for not getting rides",
    #     system_prompt=not_getting_rides_system_prompt[0]["content"],
    #     tools=ToolsSchema(standard_tools=[driver_info,send_dummy_request,send_overlay_sms])
    # )

    # movies_config = AgentConfig(
    #     name="movies",
    #     description="Agent for movies",
    #     system_prompt=movies_system_prompt[0]["content"],
    #     tools=ToolsSchema(standard_tools=[search_movies, get_movie_details])
    # )

    # agents = {"router": (router_llm, router_config), "not_getting_rides": (not_getting_rides_llm, not_getting_rides_config), "movies": (moive_agent, movies_config)}
    # routerLLM = AgentRouter(agents=agents, initial_agent="router")

    # context = routerLLM.get_current_context()
    # context_aggregator = LLMContextAggregatorPair(context)


    agent_for_not_getting_rides = OpenAILLMService(api_key=config.OPENAI_API_KEY)


    tools = ToolsSchema(standard_tools=[driver_info,send_dummy_request,send_overlay_sms])

    messages = not_getting_rides_system_prompt

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
    
    agent_for_not_getting_rides.register_function("get_driver_info", get_driver_info_wrapper)
    agent_for_not_getting_rides.register_function("send_dummy_request", send_dummy_notification_wrapper)
    agent_for_not_getting_rides.register_function("send_overlay_sms", send_overlay_sms_wrapper)

   


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
        audio_in_filter=KoalaFilter(access_key=config.KOALA_ACCESS_KEY),
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
            agent_for_not_getting_rides,  # LLM
            # routerLLM,
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
        
        # Update session with connection info
        await session_manager.set_value(session_id, "connected_at", datetime.now().isoformat())
        await session_manager.set_value(session_id, "status", "connected")
        
        # Example: Retrieve session data
        session_data = await session_manager.get_session(session_id)
        logger.info(f"Session data: {session_data}")
        
        # Kick off the conversation.
        # messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMRunFrame()])


    # @routerLLM.event_handler("on_agent_switched")
    # async def on_agent_switched(routerLLM, from_agent: str, to_agent: str):
    #     logger.info(f"[log from event handler]: Agent switched from {from_agent} to {to_agent}")
        
    #     # Get the current context (new agent's context)
    #     # Context is already cleared in handoff, we just need to add greeting
    #     current_context = routerLLM.get_current_context()
        
    #     # Get current messages (should only have system messages after handoff cleared it)
    #     all_messages = current_context.get_messages()
    #     logger.info(f"[log from event handler]: Messages after handoff clear: {all_messages}")

    #     # Add greeting instruction as a system message

    #     # Add greeting to existing system messages
    #     current_context.set_messages(all_messages)
        
    #     logger.info(f"Greeting instruction added for agent: {to_agent}")
        
    #     # Trigger the agent to speak the greeting
    #     await task.queue_frames([
    #         LLMContextFrame(context=current_context),
    #         LLMRunFrame()
    #     ])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        
        # Update session with disconnection info
        await session_manager.set_value(session_id, "disconnected_at", datetime.now().isoformat())
        await session_manager.set_value(session_id, "status", "disconnected")
        
        # Example: Retrieve final session data before cleanup
        final_session_data = await session_manager.get_session(session_id)
        logger.info(f"Final session data: {final_session_data}")
        
        # Optionally delete session or keep it for analytics
        # await session_manager.delete_session(session_id)
        
        # Stop and save the audio recording
        # audio_recorder.stop_recording() 
        await task.cancel()

    # @transport.event_handler("on_user_started_speaking")
    # async def on_user_started_speaking(transport):
    #     logger.info("User started speaking - cancelling current bot operation")
    #     # Cancel any ongoing LLM/TTS operations when user interrupts
    #     await task.queue_frames([CancelFrame()])

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