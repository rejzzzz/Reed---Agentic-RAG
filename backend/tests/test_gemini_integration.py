import pytest
from app.services.llm.factory import LLMFactory
from langchain_core.messages import HumanMessage
import os

@pytest.mark.asyncio
async def test_gemini_api_key_works():
    # Only run this test if the API key is actually set in the environment
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        pytest.skip("GEMINI_API_KEY is not set or is a placeholder. Skipping integration test.")
        
    try:
        # Initialize the Gemini LLM
        llm = LLMFactory.create_llm(provider="gemini")
        
        # Send a simple query to the model
        response = llm.invoke([HumanMessage(content="Reply with exactly the word 'SUCCESS'.")])
        
        assert response is not None
        assert response.content != ""
        print(f"Gemini Response: {response.content}")
        
    except Exception as e:
        pytest.fail(f"Gemini API call failed: {e}")
