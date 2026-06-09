import os
from .base import BaseProvider
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

class GroqProvider(BaseProvider):
    @classmethod
    def get_name(cls) -> str:
        return "groq"
        
    @classmethod
    def create_llm(cls, **kwargs) -> BaseChatModel:
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("Please install langchain-groq to use the Groq provider.")
            
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
            
        model_name = kwargs.get("model_name", settings.GROQ_MODEL)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        return ChatGroq(api_key=api_key, model_name=model_name, temperature=temperature)
