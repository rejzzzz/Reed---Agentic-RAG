def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "API is running smoothly."
    }

def test_list_providers(client):
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    data = response.json()
    assert "available_providers" in data
    assert isinstance(data["available_providers"], list)
