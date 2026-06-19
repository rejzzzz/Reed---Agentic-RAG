from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import retrieve, rerank_documents, grade_documents, generate, handle_no_context
from .web_search import web_search

def check_relevance(state: GraphState):
    """
    Determine the next node based on relevance grading.
    """
    relevant_docs = state.get("relevant_documents", [])
    if len(relevant_docs) == 0:
        return "web_search"
    return "generate"

def check_web_search(state: GraphState):
    relevant_docs = state.get("relevant_documents", [])
    if len(relevant_docs) == 0:
        return "handle_no_context"
    return "generate"

def build_agent_graph():
    """
    Builds and compiles the LangGraph workflow for the Agentic RAG.
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("rerank_documents", rerank_documents)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("web_search", web_search)
    workflow.add_node("generate", generate)
    workflow.add_node("handle_no_context", handle_no_context)
    
    # Define edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "rerank_documents")
    workflow.add_edge("rerank_documents", "grade_documents")
    
    # Conditional Edge from grade_documents
    workflow.add_conditional_edges(
        "grade_documents",
        check_relevance,
        {
            "generate": "generate",
            "web_search": "web_search"
        }
    )
    
    # Conditional Edge from web_search
    workflow.add_conditional_edges(
        "web_search",
        check_web_search,
        {
            "generate": "generate",
            "handle_no_context": "handle_no_context"
        }
    )
    
    workflow.add_edge("generate", END)
    workflow.add_edge("handle_no_context", END)
    
    # Compile the graph
    app = workflow.compile()
    return app

# Expose the compiled graph
agent_app = build_agent_graph()
