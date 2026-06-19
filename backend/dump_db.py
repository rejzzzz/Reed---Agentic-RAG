import chromadb
from pathlib import Path

client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_collection("document_chunks")
data = collection.get()

for i in range(len(data['ids'])):
    print(f"--- Chunk {i} ---")
    print(f"Source: {data['metadatas'][i].get('source_document')}")
    print(data['documents'][i][:200])
    print("\n")
