from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.llm import GoogleLLMService
from app.core import config


def get_llm_service():
    if config.LLM_PROVIDER == "openai":
        return OpenAILLMService(api_key=config.OPENAI_API_KEY)
    elif config.LLM_PROVIDER == "gemini":
        return GoogleLLMService(api_key=config.GEMINI_API_KEY)
    else:
        raise ValueError(f"Invalid LLM service: {config.LLM_SERVICE}")