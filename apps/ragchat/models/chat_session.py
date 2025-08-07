from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # Optional metadata
    description: Optional[str] = Field(default=None, max_length=1000)
    user_id: Optional[str] = Field(default=None, max_length=255)
    
    # Relationships
    messages: List["Message"] = Relationship(back_populates="chat_session")
    
    class Config:
        arbitrary_types_allowed = True 