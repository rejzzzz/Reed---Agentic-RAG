# Reed — Agentic RAG System

Reed is a modern, modular Retrieval-Augmented Generation (RAG) system built with FastAPI, LangGraph, and Next.js. It features multimodal PDF processing, an intelligent agentic reasoning pipeline with reranking and web search fallbacks, and a beautiful streaming frontend interface.

![App Screenshot](images/image.png)

## Features

- **Agentic Pipeline**: Built with LangGraph, the system intelligently retrieves, reranks, and grades documents. If no relevant documents are found, it falls back to a web search.
- **Multimodal PDF Processing**: Extracts text and images from PDFs (OCR ready).
- **Streaming Chat**: Server-Sent Events (SSE) provide real-time token-by-token generation for a snappy user experience.
- **Conversation Memory**: Chats are persisted automatically to a local SQLite database, so you can revisit past conversations.
- **Document Management**: Manage your vector database (ChromaDB) directly from the frontend library view.
- **Swappable LLMs**: Easily switch between Groq, Anthropic, Ollama, and AWS Bedrock.

## Architecture

```mermaid
graph TD
    User([User]) --> |Queries| UI[Next.js Frontend]
    UI --> |/chat/stream| API[FastAPI Backend]
    
    subgraph Agentic RAG [LangGraph Workflow]
        A(Retrieve) --> B(Rerank with BM25)
        B --> C(Grade Documents)
        C -->|Relevant| D(Generate)
        C -->|Irrelevant| E(Web Search Fallback)
        E -->|Search Context| D
    end
    
    API --> Agentic RAG
    A --> ChromaDB[(ChromaDB)]
    D --> |Streaming Response| UI
```

## Quickstart

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.template .env
# Edit .env and add your GROQ_API_KEY

# Start the server
uvicorn main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Navigate to `http://localhost:3000` in your browser.

## API Endpoints

- `POST /api/v1/upload` - Upload a document and index it in ChromaDB.
- `GET /api/v1/documents` - List all indexed documents.
- `DELETE /api/v1/documents/{filename}` - Remove a document from the vector store.
- `POST /api/v1/chat` - Synchronous chat query.
- `POST /api/v1/chat/stream` - Streaming chat query via SSE.
- `GET /api/v1/chats` - List all chat sessions.
- `GET /api/v1/chats/{session_id}` - Get history for a specific session.
- `DELETE /api/v1/chats/{session_id}` - Delete a chat session.

## Configuration

You can customize the pipeline behavior in `.env` and `backend/app/config.py`:
- `RERANK_ENABLED` (default: True) - Uses BM25 to rerank retrieved chunks.
- `WEB_SEARCH_ENABLED` (default: True) - Uses DuckDuckGo search if retrieved context is irrelevant.