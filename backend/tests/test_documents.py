import io

def test_list_documents(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total_chunks" in data
    
    # We mocked 2 chunks for "test.pdf"
    assert data["total_chunks"] == 2
    assert len(data["documents"]) == 1
    assert data["documents"][0]["filename"] == "test.pdf"
    assert data["documents"][0]["chunk_count"] == 2

def test_delete_document(client):
    response = client.delete("/api/v1/documents/test.pdf")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["deleted_chunks"] == 2

def test_upload_document(client):
    # Simulate a PDF upload
    file_content = b"fake pdf content"
    files = {"file": ("test_upload.pdf", io.BytesIO(file_content), "application/pdf")}
    
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_upload.pdf"
    assert "Successfully processed" in data["status"]

def test_upload_invalid_document_type(client):
    file_content = b"fake text content"
    files = {"file": ("test_upload.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported."
