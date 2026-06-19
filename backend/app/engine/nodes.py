from typing import Dict, Any
import logging
from .state import GraphState
from ..config import settings
from ..services.vector_stores.db_manager import VectorDatabaseManager
from ..services.llm.factory import LLMFactory
from ..services.reranking.reranker import BM25Reranker
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global instances for reuse
db_manager = None
embedder = None

def get_db():
    global db_manager
    if db_manager is None:
        db_manager = VectorDatabaseManager({'chromadb': {'storage_path': settings.CHROMA_STORAGE_PATH}})
    return db_manager.get_database("chromadb")

def get_embedder():
    global embedder
    if embedder is None:
        embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return embedder

def retrieve(state: GraphState) -> Dict[str, Any]:
    """
    Retrieve documents from ChromaDB based on the question.
    """
    logger.info("---RETRIEVE--- Question: %s", state["question"])
    question = state["question"]
    
    try:
        query_vector = get_embedder().encode(question)
        
        metadata_filter = None
        document_filter = state.get("document_filter")
        if document_filter:
            metadata_filter = {"source_document": document_filter}
            
        results, _ = get_db().search(query_vector=query_vector, top_k=3, index_type="auto", metadata_filter=metadata_filter)
        documents = [res.get("text", "") for res in results]
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        documents = []
        
    return {
        "documents": documents, 
        "question": question, 
        "relevant_documents": [], 
        "provider": state.get("provider"),
        "document_filter": state.get("document_filter")
    }

def rerank_documents(state: GraphState) -> Dict[str, Any]:
    """
    Rerank documents using BM25 to prioritize the most relevant chunks.
    """
    logger.info("---RERANK DOCUMENTS---")
    question = state["question"]
    documents = state["documents"]
    
    if not settings.RERANK_ENABLED or not documents:
        return state
        
    try:
        reranker = BM25Reranker()
        reranker.fit(documents)
        
        # We don't have metadata available here right now, so we rerank just texts
        # Since reranker expects Dicts with 'text', we wrap them
        docs_to_rerank = [{"text": d} for d in documents]
        results = reranker.rerank(question, docs_to_rerank, top_k=len(documents))
        
        reranked_docs = [res["text"] for res in results]
    except Exception as e:
        logger.error(f"Reranking error: {e}")
        reranked_docs = documents
        
    return {
        **state,
        "documents": reranked_docs
    }

def grade_documents(state: GraphState) -> Dict[str, Any]:
    """
    Filter out irrelevant documents using the selected LLM provider.
    """
    logger.info("---GRADE DOCUMENTS---")
    question = state["question"]
    documents = state["documents"]
    provider = state.get("provider")
    
    try:
        llm = LLMFactory.create_llm(provider)
    except Exception as e:
        logger.error(f"Error loading LLM {provider}: {e}")
        return state
    
    relevant_docs = []
    for doc in documents:
        prompt = f"""
        You are a grader assessing relevance of a retrieved document to a user question.
        
        Retrieved document:
        {doc}
        
        User question: {question}
        
        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
        Output ONLY 'yes' or 'no' without any additional text.
        """
        
        try:
            response = llm.invoke(prompt)
            grade = response.content.strip().lower()
            if "yes" in grade:
                relevant_docs.append(doc)
        except Exception as e:
            logger.error(f"Grading error: {e}")
            relevant_docs.append(doc)
            
    return {
        "documents": documents,
        "relevant_documents": relevant_docs,
        "question": question,
        "provider": provider
    }

async def generate(state: GraphState) -> Dict[str, Any]:
    """
    Generate answer using RAG based ONLY on relevant documents.
    """
    logger.info("---GENERATE---")
    question = state["question"]
    relevant_documents = state.get("relevant_documents", [])
    provider = state.get("provider")
    
    try:
        llm = LLMFactory.create_llm(provider)
    except Exception as e:
        return {**state, "generation": f"Configuration Error: {e}"}
    
    context = "\n\n".join(relevant_documents)
    
    prompt = f"""
    You are a helpful assistant for question-answering tasks.
    Use the following pieces of retrieved context to answer the question. 
    If you don't know the answer, just say that you don't know. 
    Use three sentences maximum and keep the answer concise.
    
    Question: {question} 
    
    Context: {context} 
    
    Answer:
    """
    
    try:
        response = await llm.ainvoke(prompt)
        generation = response.content
    except Exception as e:
        logger.error(f"Generation error: {e}")
        generation = "I apologize, but I encountered an error while trying to generate the answer."
        
    return {
        "documents": state["documents"],
        "relevant_documents": relevant_documents,
        "question": question,
        "generation": generation,
        "provider": provider
    }

def handle_no_context(state: GraphState) -> Dict[str, Any]:
    """
    Fallback node when no relevant documents are found.
    """
    logger.info("---HANDLE NO CONTEXT---")
    return {
        "documents": state["documents"],
        "relevant_documents": [],
        "question": state["question"],
        "generation": "I'm sorry, but I couldn't find any relevant information in the uploaded documents to answer your question.",
        "provider": state.get("provider")
    }
