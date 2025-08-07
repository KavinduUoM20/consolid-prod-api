from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from apps.ragchat.models.message import MessageRole

class ChatSessionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    user_id: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    user_id: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    role: MessageRole = MessageRole.USER
    chat_session_id: str

class MessageResponse(BaseModel):
    id: str
    content: str
    role: MessageRole
    created_at: datetime
    chat_session_id: str
    sources: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None

class ChatMessageRequest(BaseModel):
    message: str
    chat_session_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    message: MessageResponse
    chat_session: ChatSessionResponse 