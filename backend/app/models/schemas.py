from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    question: str = Field(..., description="The user's query to the Agentic RAG system.")
    provider: Optional[str] = Field(None, description="The LLM provider to use (e.g. 'groq', 'aws'). Defaults to the server config.")
    session_id: Optional[str] = Field(None, description="The session ID to persist chat memory across requests.")
    document: Optional[str] = Field(None, description="The document filename to scope the chat to.")

class ChatResponse(BaseModel):
    question: str
    generation: str
    provider_used: str
    session_id: Optional[str] = None
