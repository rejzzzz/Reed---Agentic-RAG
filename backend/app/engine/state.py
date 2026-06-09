from typing import TypedDict, List, Optional

class GraphState(TypedDict):
    """
    Represents the state of our agentic RAG graph.
    """
    question: str
    documents: List[str]          # All retrieved documents
    relevant_documents: List[str] # Filtered documents after grading
    generation: str
    provider: Optional[str]       # Which LLM provider to use
