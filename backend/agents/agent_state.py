"""
LangGraph State Definition for Multi-Agent Workflow
"""
from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    """
    State object passed between agents in the workflow

    This state is maintained throughout the entire agent pipeline
    and each agent can read from and write to it.
    """

    # Input
    query: str                          # User's question
    top_k: int                          # Number of chunks to retrieve
    source: Optional[str]               # Document source filter (legacy)
    doc_ids: Optional[List[str]]        # Phase 5: Document IDs to search
    use_multi_doc: bool                 # Phase 5: Use multi-doc store
    conversation_context: str           # Previous conversation history

    # Research Agent Output
    chunks: List[str]                   # Retrieved text chunks
    sources: List[str]                  # Source documents for chunks
    num_chunks_found: int               # Number of chunks retrieved
    searched_docs: List[str]            # Phase 5: Documents that were searched

    # Summarizer Agent Output
    initial_summary: str                # First draft answer

    # Critic Agent Output
    critique: str                       # Quality evaluation
    has_gaps: bool                      # Whether answer needs improvement
    suggestions: List[str]              # Improvement suggestions

    # Editor Agent Output
    final_answer: str                   # Polished final answer
    editing_applied: bool               # Whether editing was needed

    # Workflow Metadata
    workflow_log: List[str]             # Progress logs (simple strings)
    status: str                         # Current workflow status
    error_message: Optional[str]        # Error details if any

    # Agent execution flags
    research_complete: bool
    summary_complete: bool
    critique_complete: bool
    editor_complete: bool
