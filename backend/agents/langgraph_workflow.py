"""
LangGraph Workflow Definition for Multi-Agent System

This creates a state graph with conditional routing:
Research → Summarize → Critique → [Edit OR Skip] → End
"""
from langgraph.graph import StateGraph, END
from agents.agent_state import AgentState
from agents.langgraph_nodes import (
    research_node,
    summarizer_node,
    critic_node,
    editor_node,
    skip_editor_node,
    should_edit
)


def create_agent_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow

    Workflow:
    1. Research Agent retrieves relevant chunks
    2. Summarizer Agent creates initial answer
    3. Critic Agent evaluates quality
    4. Conditional routing:
       - If gaps found → Editor Agent polishes
       - If no gaps → Skip to end (use initial summary)

    Returns:
        Compiled StateGraph ready for execution
    """

    # Create workflow graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("summarize", summarizer_node)
    workflow.add_node("critique", critic_node)
    workflow.add_node("edit", editor_node)
    workflow.add_node("skip_edit", skip_editor_node)

    # Set entry point
    workflow.set_entry_point("research")

    # Add edges (sequential flow)
    workflow.add_edge("research", "summarize")
    workflow.add_edge("summarize", "critique")

    # Add conditional routing after critique
    workflow.add_conditional_edges(
        "critique",
        should_edit,  # Decision function
        {
            "edit": "edit",           # If gaps found, go to editor
            "skip_edit": "skip_edit"  # If no gaps, skip editing
        }
    )

    # Both paths lead to END
    workflow.add_edge("edit", END)
    workflow.add_edge("skip_edit", END)

    # Compile graph
    return workflow.compile()


def get_workflow_visualization() -> str:
    """
    Get Mermaid diagram of the workflow

    Returns:
        Mermaid markdown string for visualization
    """
    graph = create_agent_workflow()

    try:
        # LangGraph can export to Mermaid format
        mermaid = graph.get_graph().draw_mermaid()
        return mermaid
    except Exception as e:
        # Fallback: manual diagram
        return """
graph TD
    START([Start]) --> research[Research Agent]
    research --> summarize[Summarizer Agent]
    summarize --> critique[Critic Agent]
    critique -->|Has Gaps| edit[Editor Agent]
    critique -->|No Gaps| skip[Skip Editor]
    edit --> END([End])
    skip --> END
"""


# Create singleton workflow instance
agent_workflow = create_agent_workflow()
