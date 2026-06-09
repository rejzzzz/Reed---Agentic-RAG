import os
from .base import BaseProvider
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

class AnthropicProvider(BaseProvider):
    @classmethod
    def get_name(cls) -> str:
        return "anthropic"
        
    @classmethod
    def create_llm(cls, **kwargs) -> BaseChatModel:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Please install langchain-anthropic to use the Anthropic provider.")
            
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
            
        model_name = kwargs.get("model_name", settings.ANTHROPIC_MODEL)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        return ChatAnthropic(api_key=api_key, model=model_name, temperature=temperature)
