import pytest
from app.services.llm.factory import LLMFactory
from langchain_core.messages import HumanMessage
import os

@pytest.mark.asyncio
async def test_groq_api_key_works():
    # Only run this test if the API key is actually set in the environment
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY is not set. Skipping integration test.")
        
    try:
        # Initialize the Groq LLM
        llm = LLMFactory.create_llm(provider="groq")
        
        # Send a simple query to the model
        response = llm.invoke([HumanMessage(content="Reply with exactly the word 'SUCCESS'.")])
        
        assert response is not None
        assert response.content != ""
        print(f"Groq Response: {response.content}")
        
    except Exception as e:
        pytest.fail(f"Groq API call failed: {e}")
