import os
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transcriptions.language import Language

from app.core import config


def get_tts_service(language: str):
    if config.TTS_PROVIDER == "sarvam":
        return SarvamTTSService(
            api_key=config.SARVAM_API_KEY,
            voice_id="manisha",
            model="bulbul:v2",
            params=SarvamTTSService.InputParams(
                language=Language.TA
                if language == "ta"
                else Language.KN
                if language == "kn"
                else Language.HI
                if language == "hi"
                else Language.ML
                if language == "ml"
                else Language.EN,
                pitch=config.SARVAM_PITCH,
                pace=config.SARVAM_PACE,
            )
        )
    elif config.TTS_PROVIDER == "google":
        return GoogleTTSService(
            voice_id="ml-IN-Chirp3-HD-Autonoe" if language == "ml" else "kn-IN-Chirp3-HD-Autonoe" if language == "kn" else "ta-IN-Chirp3-HD-Autonoe" if language == "ta" else "hi-IN-Chirp3-HD-Autonoe",
            params=GoogleTTSService.InputParams(
                language=Language.TA
                if language == "ta"
                else Language.KA
                if language == "ka"
                else Language.HI
                if language == "hi"
                else Language.ML
            ),
            credentials=config.GOOGLE_TEST_CREDENTIALS,
            interim_results=True,
        )

    elif config.TTS_PROVIDER == "openai":
        return OpenAITTSService(
            api_key=config.OPENAI_API_KEY,
            voice="ballad",
            language = Language.TA_IN if language == "ta" else Language.KN_IN if language == "kn" else Language.HI_IN,
        )
    else:
        raise ValueError(f"Invalid TTS provider: {config.TTS_PROVIDER}")    