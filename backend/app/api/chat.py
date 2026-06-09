import os
import tempfile
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
import logging

from ..models.schemas import ChatRequest, ChatResponse
from ..engine.graph import agent_app
from ..config import settings
from ..services.data_processing.pdf_processor import MultimodalPDFProcessor
from ..services.chunking.semantic_chunker import SemanticChunker
from ..services.vector_stores.db_manager import VectorDatabaseManager
from ..services.llm.factory import LLMFactory

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
        initial_state = {
            "question": request.question, 
            "documents": [], 
            "relevant_documents": [],
            "generation": "",
            "provider": request.provider
        }
        
        # Invoke the graph (synchronously for simplicity, can be updated for streaming later)
        result = agent_app.invoke(initial_state)
        
        return ChatResponse(
            question=result.get("question", request.question),
            generation=result.get("generation", ""),
            provider_used=result.get("provider") or "default"
        )
    except Exception as e:
        logger.error(f"Chat execution failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during chat generation.")

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
                'text_extraction': {'preserve_layout': True, 'extract_images': False, 'ocr_enabled': False},
                'table_extraction': {'method': 'pdfplumber'},
                'image_processing': {'extract_images': False, 'ocr_images': False}
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
