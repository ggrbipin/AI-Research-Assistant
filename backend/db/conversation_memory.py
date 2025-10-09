"""
In-Memory Conversation Manager
Stores conversation history for each session to enable follow-up queries
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from utils.logger import db_logger


class ConversationMemory:
    """
    Manages conversation history in-memory using Python dictionaries
    """

    def __init__(self):
        # Structure: {session_id: {messages: [], metadata: {}}}
        self.sessions: Dict[str, Dict] = {}
        db_logger.info("ConversationMemory initialized")

    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new conversation session

        Args:
            session_id: Optional custom session ID, generates UUID if not provided

        Returns:
            session_id: The created session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "messages": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "message_count": 0
                }
            }
            db_logger.info(f"Created new session: {session_id}")
        else:
            db_logger.debug(f"Session already exists: {session_id}")

        return session_id

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add a message to the conversation history

        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (sources, workflow_log, etc.)
        """
        if session_id not in self.sessions:
            db_logger.warning(f"Session {session_id} not found, creating new session")
            self.create_session(session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.sessions[session_id]["messages"].append(message)
        self.sessions[session_id]["metadata"]["last_updated"] = datetime.now().isoformat()
        self.sessions[session_id]["metadata"]["message_count"] += 1

        db_logger.debug(f"Added {role} message to session {session_id} (total messages: {self.sessions[session_id]['metadata']['message_count']})")

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session

        Args:
            session_id: Session identifier
            limit: Optional limit on number of recent messages to return

        Returns:
            List of messages in chronological order
        """
        if session_id not in self.sessions:
            db_logger.warning(f"Session {session_id} not found for history retrieval")
            return []

        messages = self.sessions[session_id]["messages"]
        db_logger.debug(f"Retrieved history for session {session_id}: {len(messages)} messages")

        if limit:
            return messages[-limit:]

        return messages

    def get_context(self, session_id: str, max_messages: int = 10) -> str:
        """
        Get formatted conversation context for LLM prompts

        Args:
            session_id: Session identifier
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted string of conversation history
        """
        db_logger.debug(f"Getting context for session {session_id} (max_messages={max_messages})")
        messages = self.get_history(session_id, limit=max_messages)

        if not messages:
            db_logger.debug(f"No messages in session {session_id} for context")
            return ""

        context_parts = ["Previous conversation:"]
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            context_parts.append(f"{role}: {content}")

        context = "\n".join(context_parts)
        db_logger.debug(f"Generated context for session {session_id}: {len(context)} characters")
        return context

    def clear_session(self, session_id: str):
        """
        Clear conversation history for a session

        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            message_count = self.sessions[session_id]["metadata"]["message_count"]
            del self.sessions[session_id]
            db_logger.info(f"Cleared session {session_id} ({message_count} messages deleted)")
        else:
            db_logger.warning(f"Attempted to clear non-existent session: {session_id}")

    def get_all_sessions(self) -> List[str]:
        """
        Get list of all active session IDs

        Returns:
            List of session IDs
        """
        sessions = list(self.sessions.keys())
        db_logger.debug(f"Retrieved {len(sessions)} active sessions")
        return sessions

    def get_session_metadata(self, session_id: str) -> Optional[Dict]:
        """
        Get metadata for a session

        Args:
            session_id: Session identifier

        Returns:
            Session metadata or None if session doesn't exist
        """
        if session_id in self.sessions:
            db_logger.debug(f"Retrieved metadata for session {session_id}")
            return self.sessions[session_id]["metadata"]
        db_logger.warning(f"Session {session_id} not found for metadata retrieval")
        return None

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        exists = session_id in self.sessions
        db_logger.debug(f"Session exists check for {session_id}: {exists}")
        return exists


# Global instance
conversation_memory = ConversationMemory()
