from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    chat_session_id: str = Field(foreign_key="chat_sessions.id")
    role: MessageRole = Field(default=MessageRole.USER)
    content: str = Field(max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # RAG-specific fields
    sources: Optional[str] = Field(default=None, max_length=2000)  # JSON string of source documents
    tokens_used: Optional[int] = Field(default=None)
    response_time: Optional[float] = Field(default=None)  # in seconds
    
    # Relationships
    chat_session: Optional["ChatSession"] = Relationship(back_populates="messages")
    
    class Config:
        arbitrary_types_allowed = True 