import os
import tempfile
import shutil
from pathlib import Path
import json
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import logging

from ..models.schemas import ChatRequest, ChatResponse
from ..engine.graph import agent_app
from ..config import settings
from ..services.data_processing.pdf_processor import MultimodalPDFProcessor
from ..services.chunking.semantic_chunker import SemanticChunker
from ..services.vector_stores.db_manager import VectorDatabaseManager
from ..services.llm.factory import LLMFactory
from ..services.chat.memory import memory_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize DB Manager globally so connection is reused
db_manager = VectorDatabaseManager({
    'chromadb': {'storage_path': settings.CHROMA_STORAGE_PATH}
})

@router.get("/providers", tags=["LLM Configuration"])
async def list_providers():
    """
    List all dynamically loaded AI providers.
    """
    return {"available_providers": LLMFactory.get_available_providers()}

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Process a chat query using the LangGraph Agentic RAG engine.
    """
    try:
        session_id = request.session_id
        document = request.document
        
        if session_id:
            info = memory_service.get_session_info(session_id)
            if info and info.get("document"):
                document = info["document"]
        else:
            session_id = memory_service.create_session(document=document)
            
        # We fetch the last few messages for context (in a real system we'd format this into the prompt,
        # but for now we simply log it to memory)
        memory_service.add_message(session_id, "user", request.question, document=document)
        
        initial_state = {
            "question": request.question, 
            "documents": [], 
            "relevant_documents": [],
            "generation": "",
            "provider": request.provider,
            "document_filter": document
        }
        
        # Invoke the graph (synchronously for simplicity, can be updated for streaming later)
        result = agent_app.invoke(initial_state)
        
        generation = result.get("generation", "")
        provider_used = result.get("provider") or "default"
        
        memory_service.add_message(session_id, "assistant", generation, provider_used)
        
        return ChatResponse(
            question=result.get("question", request.question),
            generation=generation,
            provider_used=provider_used,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Chat execution failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during chat generation.")

@router.post("/chat/stream", tags=["Chat"])
async def chat_stream_endpoint(request: ChatRequest):
    """
    Process a chat query and stream the generation using Server-Sent Events.
    """
    session_id = request.session_id
    document = request.document
    
    if session_id:
        info = memory_service.get_session_info(session_id)
        if info and info.get("document"):
            document = info["document"]
    else:
        session_id = memory_service.create_session(document=document)
        
    memory_service.add_message(session_id, "user", request.question, document=document)
    
    async def event_generator():
        initial_state = {
            "question": request.question, 
            "documents": [], 
            "relevant_documents": [],
            "generation": "",
            "provider": request.provider,
            "document_filter": document
        }
        
        full_generation = ""
        provider_used = request.provider or "default"
        
        try:
            async for event in agent_app.astream_events(initial_state, version="v2"):
                kind = event["event"]
                # Only stream chunks that originate from the 'generate' node
                if kind == "on_chat_model_stream" and event.get("metadata", {}).get("langgraph_node") == "generate":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        full_generation += chunk
                        # Send text chunks as raw strings so frontend can just append
                        yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
                        
            memory_service.add_message(session_id, "assistant", full_generation, provider_used)
            
            yield f"event: metadata\ndata: {json.dumps({'session_id': session_id, 'provider_used': provider_used})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/chats", tags=["Chat"])
async def list_chats():
    """List all chat sessions."""
    return {"sessions": memory_service.list_sessions()}

@router.get("/chats/{session_id}", tags=["Chat"])
async def get_chat_history(session_id: str):
    """Get history for a specific chat session."""
    history = memory_service.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Chat session not found")
    info = memory_service.get_session_info(session_id)
    return {"session_id": session_id, "document": info.get("document") if info else None, "history": history}

@router.delete("/chats/{session_id}", tags=["Chat"])
async def delete_chat(session_id: str):
    """Delete a chat session."""
    success = memory_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted"}

@router.get("/documents", tags=["Documents"])
async def list_documents():
    """List all indexed documents in the knowledge base."""
    try:
        db = db_manager.get_database("chromadb")
        collection = db.collections.get('default')
        if not collection:
            return {"documents": [], "total_chunks": 0}

        all_data = collection.get(include=["metadatas"])
        metadatas = all_data.get("metadatas", [])

        doc_map = {}
        for meta in metadatas:
            source = meta.get("source_document", "unknown")
            if source not in doc_map:
                doc_map[source] = {"filename": source, "chunk_count": 0}
            doc_map[source]["chunk_count"] += 1

        return {
            "documents": list(doc_map.values()),
            "total_chunks": len(metadatas)
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")

@router.delete("/documents/{filename}", tags=["Documents"])
async def delete_document(filename: str):
    """Remove a document and all its chunks from the knowledge base."""
    try:
        db = db_manager.get_database("chromadb")
        collection = db.collections.get('default')
        if not collection:
            raise HTTPException(status_code=404, detail="No collection found")

        results = collection.get(
            where={"source_document": filename},
            include=[]
        )
        ids = results.get("ids", [])
        if not ids:
            raise HTTPException(status_code=404, detail=f"No chunks found for '{filename}'")

        collection.delete(ids=ids)
        return {"filename": filename, "deleted_chunks": len(ids)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

@router.post("/upload", tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint for PDF document ingestion.
    Extracts text, semantically chunks it, and embeds into ChromaDB.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_pdf_path = Path(temp_dir) / file.filename
            
            # Save uploaded file
            with open(temp_pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # 1. Parse PDF using their custom processor
            processor = MultimodalPDFProcessor({
                'text_extraction': {'preserve_layout': True, 'extract_images': True, 'ocr_enabled': True},
                'table_extraction': {'method': 'pdfplumber'},
                'image_processing': {'extract_images': True, 'ocr_images': True}
            })
            results = processor.process_directory(temp_dir)
            documents = results.get("documents", [])
            
            if not documents:
                raise Exception("Failed to extract content from PDF")
                
            # 2. Semantic Chunking & Embeddings
            chunker = SemanticChunker({
                'chunk_size': settings.CHUNK_SIZE,
                'chunk_overlap': settings.CHUNK_OVERLAP,
                'embeddings': {'model_name': settings.EMBEDDING_MODEL, 'batch_size': 32}
            })
            chunks = chunker.process_documents(documents)
            
            # Convert SemanticChunk objects to dictionaries for the db_manager
            chunk_dicts = [c.to_dict() for c in chunks]
            
            # 3. Vector DB Insertion
            setup_results = db_manager.setup_all_databases(chunk_dicts)
            if not setup_results.get('chromadb', False):
                raise Exception("Failed to insert chunks into ChromaDB")
            
        return {"filename": file.filename, "status": f"Successfully processed and embedded {len(chunks)} chunks"}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
