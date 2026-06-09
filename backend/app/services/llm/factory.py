import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type
from langchain_core.language_models.chat_models import BaseChatModel
from .providers.base import BaseProvider
from app.config import settings

class LLMFactory:
    """
    Factory class to instantiate LLM clients using a plugin architecture.
    Auto-discovers providers in the 'providers' directory.
    """
    _registry: Dict[str, Type[BaseProvider]] = {}
    _is_initialized = False
    
    @classmethod
    def _initialize(cls):
        if cls._is_initialized:
            return
            
        providers_dir = Path(__file__).parent / "providers"
        
        for file in providers_dir.glob("*_provider.py"):
            module_name = f".providers.{file.stem}"
            try:
                module = importlib.import_module(module_name, package="app.services.llm")
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseProvider) and obj is not BaseProvider:
                        cls._registry[obj.get_name().lower()] = obj
            except Exception as e:
                print(f"Warning: Failed to load provider module {file.stem}: {e}")
                    
        cls._is_initialized = True
        
    @classmethod
    def get_available_providers(cls) -> List[str]:
        cls._initialize()
        return list(cls._registry.keys())
        
    @classmethod
    def create_llm(cls, provider: str = None, **kwargs) -> BaseChatModel:
        cls._initialize()
        provider = provider or settings.LLM_PROVIDER
        provider = provider.lower()
        
        if provider not in cls._registry:
            raise ValueError(f"Provider '{provider}' not found. Available: {cls.get_available_providers()}")
            
        provider_class = cls._registry[provider]
        return provider_class.create_llm(**kwargs)

def get_default_llm() -> BaseChatModel:
    return LLMFactory.create_llm()
