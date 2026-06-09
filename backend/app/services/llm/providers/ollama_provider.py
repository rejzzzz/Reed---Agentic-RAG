import os
from .base import BaseProvider
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

class OllamaProvider(BaseProvider):
    @classmethod
    def get_name(cls) -> str:
        return "ollama"
        
    @classmethod
    def create_llm(cls, **kwargs) -> BaseChatModel:
        try:
            from langchain_community.chat_models import ChatOllama
        except ImportError:
            raise ImportError("Please install langchain-community to use Ollama.")
            
        model_name = kwargs.get("model_name", settings.OLLAMA_MODEL)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        base_url = os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)
        return ChatOllama(model=model_name, base_url=base_url, temperature=temperature)
