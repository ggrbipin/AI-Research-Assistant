"""
Orchestrator: Coordinates the multi-agent workflow using LangGraph

This replaces the previous custom implementation with LangGraph's
state graph for better flexibility, conditional routing, and visualization.
"""
from typing import List, Optional
from agents.langgraph_workflow import agent_workflow
from agents.agent_state import AgentState


class Orchestrator:
    def __init__(self):
        self.workflow = agent_workflow

    def process_query(self, query: str, top_k: int = 5, source: str = None, conversation_context: str = ""):
        """
        Process a user query through the LangGraph multi-agent pipeline

        Workflow (with conditional routing):
        1. Research Agent -> Retrieve relevant chunks from FAISS
        2. Summarizer Agent -> Create initial summary (with conversation context)
        3. Critic Agent -> Evaluate and provide feedback
        4. Conditional:
           - If gaps found -> Editor Agent polishes answer
           - If no gaps -> Skip to end (use initial summary)

        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            source: Optional document source filter
            conversation_context: Previous conversation history for follow-up queries

        Returns:
            dict containing final answer and workflow metadata
        """

        # Initialize state
        initial_state: AgentState = {
            # Input
            "query": query,
            "top_k": top_k,
            "source": source,
            "conversation_context": conversation_context,

            # Outputs (will be populated by agents)
            "chunks": [],
            "sources": [],
            "num_chunks_found": 0,
            "initial_summary": "",
            "critique": "",
            "has_gaps": False,
            "suggestions": [],
            "final_answer": "",
            "editing_applied": False,

            # Metadata
            "workflow_log": [],
            "status": "initialized",
            "error_message": None,

            # Execution flags
            "research_complete": False,
            "summary_complete": False,
            "critique_complete": False,
            "editor_complete": False,
        }

        try:
            # Execute LangGraph workflow
            final_state = self.workflow.invoke(initial_state)

            # Check for errors
            if final_state.get("status") == "error":
                return {
                    "status": "error",
                    "answer": final_state.get("error_message", "Unknown error occurred"),
                    "workflow_log": final_state.get("workflow_log", [])
                }

            # Return successful result
            return {
                "status": "success",
                "answer": final_state["final_answer"],
                "sources": final_state.get("sources", []),
                "workflow_log": final_state.get("workflow_log", []),
                "metadata": {
                    "num_chunks": final_state.get("num_chunks_found", 0),
                    "initial_summary_length": len(final_state.get("initial_summary", "")),
                    "final_answer_length": len(final_state["final_answer"]),
                    "critique_applied": final_state.get("critique_complete", False),
                    "editing_applied": final_state.get("editing_applied", False),
                    "has_gaps": final_state.get("has_gaps", False),
                    "workflow_type": "langgraph"
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "answer": f"Error in LangGraph workflow: {str(e)}",
                "workflow_log": [],
                "metadata": {}
            }

    def process_query_multi_doc(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 5,
        conversation_context: str = ""
    ):
        """
        Phase 5: Process query using multi-document store with context switching

        Args:
            query: User's question
            doc_ids: List of document IDs to search (None = all docs)
            top_k: Number of chunks to retrieve
            conversation_context: Previous conversation history

        Returns:
            dict containing final answer and workflow metadata
        """

        # Initialize state with multi-doc parameters
        initial_state: AgentState = {
            # Input
            "query": query,
            "top_k": top_k,
            "source": None,  # Not used in multi-doc mode
            "doc_ids": doc_ids,  # Phase 5: Document selection
            "use_multi_doc": True,  # Flag for multi-doc mode
            "conversation_context": conversation_context,

            # Outputs (will be populated by agents)
            "chunks": [],
            "sources": [],
            "num_chunks_found": 0,
            "initial_summary": "",
            "critique": "",
            "has_gaps": False,
            "suggestions": [],
            "final_answer": "",
            "editing_applied": False,
            "searched_docs": [],  # Track which docs were searched

            # Metadata
            "workflow_log": [],
            "status": "initialized",
            "error_message": None,

            # Execution flags
            "research_complete": False,
            "summary_complete": False,
            "critique_complete": False,
            "editor_complete": False,
        }

        try:
            # Execute LangGraph workflow
            final_state = self.workflow.invoke(initial_state)

            # Check for errors
            if final_state.get("status") == "error":
                return {
                    "status": "error",
                    "answer": final_state.get("error_message", "Unknown error occurred"),
                    "workflow_log": final_state.get("workflow_log", []),
                    "searched_docs": final_state.get("searched_docs", [])
                }

            # Return successful result
            return {
                "status": "success",
                "answer": final_state["final_answer"],
                "sources": final_state.get("sources", []),
                "searched_docs": final_state.get("searched_docs", []),
                "workflow_log": final_state.get("workflow_log", []),
                "metadata": {
                    "num_chunks": final_state.get("num_chunks_found", 0),
                    "initial_summary_length": len(final_state.get("initial_summary", "")),
                    "final_answer_length": len(final_state["final_answer"]),
                    "critique_applied": final_state.get("critique_complete", False),
                    "editing_applied": final_state.get("editing_applied", False),
                    "has_gaps": final_state.get("has_gaps", False),
                    "workflow_type": "langgraph-multi-doc",
                    "searched_docs": final_state.get("searched_docs", [])
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "answer": f"Error in multi-doc workflow: {str(e)}",
                "workflow_log": [],
                "searched_docs": [],
                "metadata": {}
            }

    def get_workflow_diagram(self) -> str:
        """
        Get visual representation of the workflow

        Returns:
            Mermaid markdown diagram
        """
        from agents.langgraph_workflow import get_workflow_visualization
        return get_workflow_visualization()
