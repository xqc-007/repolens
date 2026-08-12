from app.core.config import get_settings
from app.integrations.llm.mock import MockLLMProvider
from app.integrations.llm.openai_provider import OpenAIProvider

def get_llm_provider():
    return MockLLMProvider() if get_settings().llm_mode=="mock" else OpenAIProvider()
