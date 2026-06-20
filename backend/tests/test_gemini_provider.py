import os
import pytest
from unittest.mock import patch

from app.services.llm.providers.gemini_provider import GeminiProvider
from app.config import settings

def test_gemini_provider_name():
    assert GeminiProvider.get_name() == "gemini"

@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_gemini_provider_create_llm_success(mock_chat_model):
    # Temporarily set the environment variable
    original_key = os.getenv("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "fake_gemini_api_key"
    
    try:
        llm = GeminiProvider.create_llm()
        
        # Verify that ChatGoogleGenerativeAI was initialized correctly
        mock_chat_model.assert_called_once_with(
            google_api_key="fake_gemini_api_key",
            model=settings.GEMINI_MODEL,
            temperature=settings.LLM_TEMPERATURE
        )
    finally:
        # Restore environment
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        else:
            del os.environ["GEMINI_API_KEY"]

@patch("langchain_google_genai.ChatGoogleGenerativeAI")
def test_gemini_provider_create_llm_with_kwargs(mock_chat_model):
    original_key = os.getenv("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "fake_gemini_api_key"
    
    try:
        llm = GeminiProvider.create_llm(model_name="gemini-1.5-pro", temperature=0.7)
        
        mock_chat_model.assert_called_once_with(
            google_api_key="fake_gemini_api_key",
            model="gemini-1.5-pro",
            temperature=0.7
        )
    finally:
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        else:
            del os.environ["GEMINI_API_KEY"]

def test_gemini_provider_missing_api_key():
    # Remove the API key if it exists
    original_key = os.getenv("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
        
    try:
        with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable is not set."):
            GeminiProvider.create_llm()
    finally:
        # Restore
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
