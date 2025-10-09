"""
SQLite-based Conversation Memory
Provides persistent storage for conversation history
"""
import sqlite3
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from utils.logger import db_logger


class SQLiteConversationMemory:
    """
    Manages conversation history with SQLite persistent storage
    """

    def __init__(self, db_path: str = None):
        """
        Initialize SQLite conversation memory

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = os.getenv("CONVERSATION_DB_PATH", "db/conversations.db")

        self.db_path = db_path
        db_logger.info(f"Initializing SQLite conversation memory: {db_path}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_db()
        db_logger.info("SQLite conversation memory initialized")

    def _init_db(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                message_count INTEGER DEFAULT 0
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp
            ON messages(timestamp)
        """)

        conn.commit()
        conn.close()
        db_logger.debug("Database tables initialized")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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

        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if session already exists
        cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
        existing = cursor.fetchone()

        if not existing:
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO sessions (session_id, created_at, last_updated, message_count)
                VALUES (?, ?, ?, 0)
            """, (session_id, now, now))
            conn.commit()
            db_logger.info(f"Created new session: {session_id}")
        else:
            db_logger.debug(f"Session already exists: {session_id}")

        conn.close()
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a message to the conversation history

        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (sources, workflow_log, etc.)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Ensure session exists
        cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
        if not cursor.fetchone():
            db_logger.warning(f"Session {session_id} not found, creating new session")
            conn.close()
            self.create_session(session_id)
            conn = self._get_connection()
            cursor = conn.cursor()

        # Insert message
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute("""
            INSERT INTO messages (session_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, role, content, now, metadata_json))

        # Update session metadata
        cursor.execute("""
            UPDATE sessions
            SET last_updated = ?, message_count = message_count + 1
            WHERE session_id = ?
        """, (now, session_id))

        conn.commit()

        # Get updated message count
        cursor.execute("SELECT message_count FROM sessions WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()[0]

        conn.close()
        db_logger.debug(f"Added {role} message to session {session_id} (total messages: {count})")

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session

        Args:
            session_id: Session identifier
            limit: Optional limit on number of recent messages to return

        Returns:
            List of messages in chronological order
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if limit:
            cursor.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()
            rows = list(reversed(rows))  # Reverse to get chronological order
        else:
            cursor.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
            """, (session_id,))
            rows = cursor.fetchall()

        messages = []
        for row in rows:
            message = {
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            }
            messages.append(message)

        conn.close()
        db_logger.debug(f"Retrieved history for session {session_id}: {len(messages)} messages")
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
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get message count before deletion
        cursor.execute("SELECT message_count FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()

        if row:
            message_count = row[0]
            # Delete messages
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            # Delete session
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            db_logger.info(f"Cleared session {session_id} ({message_count} messages deleted)")
        else:
            db_logger.warning(f"Attempted to clear non-existent session: {session_id}")

        conn.close()

    def get_all_sessions(self) -> List[str]:
        """
        Get list of all active session IDs

        Returns:
            List of session IDs
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT session_id FROM sessions ORDER BY last_updated DESC")
        rows = cursor.fetchall()
        sessions = [row["session_id"] for row in rows]

        conn.close()
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
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT created_at, last_updated, message_count
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            db_logger.debug(f"Retrieved metadata for session {session_id}")
            return {
                "created_at": row["created_at"],
                "last_updated": row["last_updated"],
                "message_count": row["message_count"]
            }

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
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM sessions WHERE session_id = ? LIMIT 1", (session_id,))
        exists = cursor.fetchone() is not None

        conn.close()
        db_logger.debug(f"Session exists check for {session_id}: {exists}")
        return exists

    def get_stats(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dictionary with database statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]

        cursor.execute("""
            SELECT AVG(message_count) FROM sessions
        """)
        avg_messages = cursor.fetchone()[0] or 0

        conn.close()

        stats = {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": round(avg_messages, 2)
        }

        db_logger.info(f"Database stats: {stats}")
        return stats


# Global instance
conversation_memory = SQLiteConversationMemory()
