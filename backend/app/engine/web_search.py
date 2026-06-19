from typing import Dict, Any
import logging
from .state import GraphState
from ..config import settings

try:
    from langchain_community.tools import DuckDuckGoSearchRun
except ImportError:
    DuckDuckGoSearchRun = None

logger = logging.getLogger(__name__)

def web_search(state: GraphState) -> Dict[str, Any]:
    """
    Perform web search when no relevant documents are found.
    """
    logger.info("---WEB SEARCH---")
    question = state["question"]
    
    if getattr(settings, "WEB_SEARCH_ENABLED", True) and DuckDuckGoSearchRun:
        try:
            search = DuckDuckGoSearchRun()
            docs = search.invoke(question)
            web_results = f"[Web Search Results]: {docs}"
            logger.info("Web search successful.")
            
            return {
                **state,
                "relevant_documents": [web_results]
            }
        except Exception as e:
            logger.error(f"Web search error: {e}")
            
    # Fallback to no context
    return {
        **state,
        "relevant_documents": []
    }
