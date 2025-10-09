"""
LangGraph Node Functions for Agent Workflow

Each function takes AgentState and returns updated AgentState
"""
from agents.agent_state import AgentState
from agents.research_agent import ResearchAgent
from agents.summarizer_agent import SummarizerAgent
from agents.critic_agent import CriticAgent
from agents.editor_agent import EditorAgent


# Initialize agents once
research_agent = ResearchAgent()
summarizer_agent = SummarizerAgent()
critic_agent = CriticAgent()
editor_agent = EditorAgent()


def research_node(state: AgentState) -> AgentState:
    """
    Research Agent Node: Retrieve relevant chunks from FAISS

    Args:
        state: Current workflow state

    Returns:
        Updated state with retrieved chunks
    """
    # Log progress
    workflow_log = state.get("workflow_log", [])

    # Check if using multi-doc mode (Phase 5)
    use_multi_doc = state.get("use_multi_doc", False)

    if use_multi_doc:
        workflow_log.append("[1/4] Research Agent: Searching multi-document store...")

        # Execute multi-doc research
        result = research_agent.search_multi_doc(
            query=state["query"],
            doc_ids=state.get("doc_ids"),
            top_k=state.get("top_k", 5)
        )

        if result["status"] == "error":
            return {
                **state,
                "status": "error",
                "error_message": result["message"],
                "workflow_log": workflow_log,
                "chunks": [],
                "sources": [],
                "searched_docs": [],
                "num_chunks_found": 0,
                "research_complete": False
            }

        workflow_log.append(
            f"[1/4] Complete - Found {len(result['chunks'])} chunks from {len(result.get('searched_docs', []))} document(s)"
        )

        return {
            **state,
            "chunks": result["chunks"],
            "sources": result["sources"],
            "searched_docs": result.get("searched_docs", []),
            "num_chunks_found": len(result["chunks"]),
            "workflow_log": workflow_log,
            "research_complete": True,
            "status": "research_complete"
        }
    else:
        # Legacy mode: single FAISS index
        workflow_log.append("[1/4] Research Agent: Searching FAISS for relevant information...")

        result = research_agent.search(
            query=state["query"],
            top_k=state.get("top_k", 5),
            source=state.get("source")
        )

        if result["status"] == "error":
            return {
                **state,
                "status": "error",
                "error_message": result["message"],
                "workflow_log": workflow_log,
                "chunks": [],
                "sources": [],
                "num_chunks_found": 0,
                "research_complete": False
            }

        workflow_log.append(f"[1/4] Complete - Found {len(result['chunks'])} relevant chunks")

        return {
            **state,
            "chunks": result["chunks"],
            "sources": result["sources"],
            "num_chunks_found": len(result["chunks"]),
            "workflow_log": workflow_log,
            "research_complete": True,
            "status": "research_complete"
        }


def summarizer_node(state: AgentState) -> AgentState:
    """
    Summarizer Agent Node: Generate initial answer from chunks

    Args:
        state: Current workflow state

    Returns:
        Updated state with initial summary
    """
    workflow_log = state.get("workflow_log", [])
    workflow_log.append("[2/4] Summarizer Agent: Creating comprehensive answer...")

    # Execute summarization
    result = summarizer_agent.summarize(
        query=state["query"],
        chunks=state["chunks"],
        conversation_context=state.get("conversation_context", "")
    )

    if result["status"] == "error":
        return {
            **state,
            "status": "error",
            "error_message": result["message"],
            "workflow_log": workflow_log,
            "initial_summary": "",
            "summary_complete": False
        }

    workflow_log.append("[2/4] Complete - Initial summary generated")

    return {
        **state,
        "initial_summary": result["summary"],
        "workflow_log": workflow_log,
        "summary_complete": True,
        "status": "summary_complete"
    }


def critic_node(state: AgentState) -> AgentState:
    """
    Critic Agent Node: Evaluate answer quality

    Args:
        state: Current workflow state

    Returns:
        Updated state with critique and recommendations
    """
    workflow_log = state.get("workflow_log", [])
    workflow_log.append("[3/4] Critic Agent: Evaluating answer quality...")

    # Execute critique
    result = critic_agent.critique(
        query=state["query"],
        summary=state["initial_summary"],
        chunks=state["chunks"]
    )

    if result["status"] == "error":
        # If critique fails, mark as no gaps (proceed with initial summary)
        workflow_log.append("[3/4] Warning - Critique failed, using initial summary")
        return {
            **state,
            "critique": "Critique unavailable",
            "has_gaps": False,
            "suggestions": [],
            "workflow_log": workflow_log,
            "critique_complete": True,
            "status": "critique_complete"
        }

    has_gaps = result.get("has_gaps", False)
    workflow_log.append(f"[3/4] Complete - Critique completed (Gaps identified: {has_gaps})")

    return {
        **state,
        "critique": result["critique"],
        "has_gaps": has_gaps,
        "suggestions": result.get("suggestions", []),
        "workflow_log": workflow_log,
        "critique_complete": True,
        "status": "critique_complete"
    }


def editor_node(state: AgentState) -> AgentState:
    """
    Editor Agent Node: Polish final answer based on critique

    Args:
        state: Current workflow state

    Returns:
        Updated state with final polished answer
    """
    workflow_log = state.get("workflow_log", [])
    workflow_log.append("[4/4] Editor Agent: Refining final answer...")

    # Execute editing
    result = editor_agent.edit(
        query=state["query"],
        summary=state["initial_summary"],
        critique=state["critique"],
        chunks=state["chunks"]
    )

    workflow_log.append("[4/4] Complete - Final answer polished and ready")

    return {
        **state,
        "final_answer": result.get("final_answer", state["initial_summary"]),
        "editing_applied": result.get("editing_applied", False),
        "workflow_log": workflow_log,
        "editor_complete": True,
        "status": "complete"
    }


def skip_editor_node(state: AgentState) -> AgentState:
    """
    Skip Editor Node: Use initial summary as final answer (no editing needed)

    Args:
        state: Current workflow state

    Returns:
        Updated state with initial summary as final answer
    """
    workflow_log = state.get("workflow_log", [])
    workflow_log.append("[4/4] Skipped - Initial summary is high quality, no editing needed")

    return {
        **state,
        "final_answer": state["initial_summary"],
        "editing_applied": False,
        "workflow_log": workflow_log,
        "editor_complete": True,
        "status": "complete"
    }


def should_edit(state: AgentState) -> str:
    """
    Conditional routing: Determine if editing is needed

    Args:
        state: Current workflow state

    Returns:
        "edit" if gaps found, "skip_edit" otherwise
    """
    # If critique identified gaps or issues, route to editor
    if state.get("has_gaps", False):
        return "edit"
    else:
        return "skip_edit"
