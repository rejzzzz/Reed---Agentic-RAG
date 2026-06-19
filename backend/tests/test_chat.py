import pytest

def test_chat_endpoint(client):
    payload = {
        "question": "What is the capital of France?",
        "provider": "mock_provider"
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["question"] == "What is the capital of France?"
    assert data["generation"] == "The capital of France is Paris."
    assert data["provider_used"] == "mock_provider"
    assert data["session_id"] == "test-session-123"

@pytest.mark.asyncio
async def test_chat_stream_endpoint(client):
    # Testing streaming endpoints via httpx can be slightly different,
    # but with TestClient we can iterate over the response
    payload = {
        "question": "What is the capital of France?",
        "provider": "mock_provider"
    }
    with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        assert response.status_code == 200
        content = response.read().decode("utf-8")
        assert "event: token" in content
        assert "The capital " in content
        assert "of France is Paris." in content
        assert "event: done" in content

def test_list_chats(client):
    response = client.get("/api/v1/chats")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["session_id"] == "test-session-123"

def test_get_chat_history(client):
    response = client.get("/api/v1/chats/test-session-123")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert len(data["history"]) == 2

def test_delete_chat(client):
    response = client.delete("/api/v1/chats/test-session-123")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}
