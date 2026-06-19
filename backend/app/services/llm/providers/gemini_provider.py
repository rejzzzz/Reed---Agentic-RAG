import os
from .base import BaseProvider
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

class GeminiProvider(BaseProvider):
    @classmethod
    def get_name(cls) -> str:
        return "gemini"
        
    @classmethod
    def create_llm(cls, **kwargs) -> BaseChatModel:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Please install langchain-google-genai to use the Gemini provider.")
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
            
        model_name = kwargs.get("model_name", settings.GEMINI_MODEL)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        return ChatGoogleGenerativeAI(google_api_key=api_key, model=model_name, temperature=temperature)
