from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.transcriptions.language import Language
from app.core import config


def get_stt_service(language: str):
    if config.STT_PROVIDER == "openai":
        return OpenAISTTService(
        api_key=config.OPENAI_API_KEY,
        model="gpt-4o-transcribe",
        language = Language.TA_IN if language == "ta" else Language.KN_IN if language == "kn" else Language.HI_IN,
    )
    elif config.STT_PROVIDER == "google":
        return GoogleSTTService(
            api_key=config.GOOGLE_API_KEY,
            model="chirp_3",
            language = Language.TA_IN if language == "ta" else Language.KN_IN if language == "kn" else Language.HI_IN if language == "hi" else Language.ML_IN,
        )
    elif config.STT_PROVIDER == "sarvam":
        return SarvamSTTService(
            api_key=config.SARVAM_API_KEY,
            model="saarika:v2.5",
            language = Language.TA_IN if language == "ta" else Language.KN_IN if language == "kn" else Language.HI_IN if language == "hi" else Language.ML_IN if language == "ml" else Language.EN_IN,
        )
    else:
        raise ValueError(f"Invalid STT provider: {config.STT_PROVIDER}")