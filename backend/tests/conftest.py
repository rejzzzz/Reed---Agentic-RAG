import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Important: import the FastAPI app
from main import app

@pytest.fixture
def client():
    """Returns a FastAPI TestClient for the app."""
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_memory_service(mocker):
    """Mocks the memory service to avoid creating actual SQLite databases during tests."""
    mock_mem = mocker.patch("app.api.chat.memory_service")
    mock_mem.create_session.return_value = "test-session-123"
    mock_mem.list_sessions.return_value = [{"session_id": "test-session-123", "created_at": "2024-01-01T00:00:00"}]
    mock_mem.get_history.return_value = [
        {"role": "user", "content": "Hello", "provider": None},
        {"role": "assistant", "content": "Hi there", "provider": "default"}
    ]
    mock_mem.delete_session.return_value = True
    return mock_mem

@pytest.fixture(autouse=True)
def mock_db_manager(mocker):
    """Mocks the VectorDatabaseManager to prevent ChromaDB creation/access."""
    mock_dbm = mocker.patch("app.api.chat.db_manager")
    
    # Mocking the database and collection
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    # Setup mock for getting collection data
    mock_collection.get.return_value = {
        "metadatas": [
            {"source_document": "test.pdf"},
            {"source_document": "test.pdf"}
        ],
        "ids": ["id1", "id2"]
    }
    mock_db.collections.get.return_value = mock_collection
    mock_dbm.get_database.return_value = mock_db
    mock_dbm.setup_all_databases.return_value = {'chromadb': True}
    
    return mock_dbm

@pytest.fixture(autouse=True)
def mock_agent_app(mocker):
    """Mocks the LangGraph agent_app so it doesn't call real LLMs."""
    mock_app = mocker.patch("app.api.chat.agent_app")
    mock_app.invoke.return_value = {
        "question": "What is the capital of France?",
        "generation": "The capital of France is Paris.",
        "provider": "mock_provider"
    }
    
    # Async generator for streaming
    async def mock_astream_events(*args, **kwargs):
        events = [
            {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="The capital ")}},
            {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="of France is Paris.")}}
        ]
        for event in events:
            yield event
            
    mock_app.astream_events = mock_astream_events
    return mock_app

@pytest.fixture(autouse=True)
def mock_document_processors(mocker):
    """Mocks the PDF processor and chunker."""
    mock_pdf = mocker.patch("app.api.chat.MultimodalPDFProcessor")
    mock_instance = mock_pdf.return_value
    mock_instance.process_directory.return_value = {"documents": [{"content": "fake content"}]}
    
    mock_chunker = mocker.patch("app.api.chat.SemanticChunker")
    mock_chunker_instance = mock_chunker.return_value
    
    # Mock chunks
    chunk_mock = MagicMock()
    chunk_mock.to_dict.return_value = {"id": "1", "text": "chunk1"}
    mock_chunker_instance.process_documents.return_value = [chunk_mock]
    
    return {"pdf": mock_pdf, "chunker": mock_chunker}
