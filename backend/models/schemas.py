from pydantic import BaseModel
from typing import Optional, List, Dict

class AskRequest(BaseModel):
    query: str
    top_k: int = 5
    source: Optional[str] = None  # Filter by document source (legacy)
    doc_ids: Optional[List[str]] = None  # Phase 5: List of document IDs to search
    session_id: Optional[str] = None  # Session ID for conversation memory

class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: str

class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict]
    metadata: Dict
