from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import retrieve, grade_documents, generate, handle_no_context

def check_relevance(state: GraphState):
    """
    Determine the next node based on relevance grading.
    """
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
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("handle_no_context", handle_no_context)
    
    # Define edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    
    # Conditional Edge
    workflow.add_conditional_edges(
        "grade_documents",
        check_relevance,
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
