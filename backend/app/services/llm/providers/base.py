from abc import ABC, abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel

class BaseProvider(ABC):
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Return the unique string identifier for this provider (e.g. 'groq')"""
        pass
        
    @classmethod
    @abstractmethod
    def create_llm(cls, **kwargs) -> BaseChatModel:
        """Instantiate and return the LangChain BaseChatModel for this provider"""
        pass
