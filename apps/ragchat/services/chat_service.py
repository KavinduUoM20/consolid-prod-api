from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional
import json

from apps.ragchat.models import ChatSession, Message
from apps.ragchat.schemas.chat import (
    ChatSessionCreate, ChatSessionResponse, 
    MessageCreate, MessageResponse,
    ChatMessageRequest, ChatMessageResponse
)
from apps.ragchat.models.message import MessageRole

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, session_data: ChatSessionCreate) -> ChatSessionResponse:
        """Create a new chat session"""
        session = ChatSession(
            title=session_data.title,
            description=session_data.description,
            user_id=session_data.user_id
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return ChatSessionResponse.from_orm(session)

    async def get_session(self, session_id: str) -> Optional[ChatSessionResponse]:
        """Get a specific chat session"""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        return ChatSessionResponse.from_orm(session) if session else None

    async def list_sessions(self, user_id: str = None) -> List[ChatSessionResponse]:
        """List all chat sessions for a user"""
        query = select(ChatSession).where(ChatSession.is_active == True)
        if user_id:
            query = query.where(ChatSession.user_id == user_id)
        query = query.order_by(ChatSession.updated_at.desc())
        
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        return [ChatSessionResponse.from_orm(session) for session in sessions]

    async def get_messages(self, session_id: str) -> Optional[List[MessageResponse]]:
        """Get all messages for a chat session"""
        # First check if session exists
        session_result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        if not session_result.scalar_one_or_none():
            return None
        
        result = await self.db.execute(
            select(Message)
            .where(Message.chat_session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        return [MessageResponse.from_orm(msg) for msg in messages]

    async def create_message(self, message_data: MessageCreate) -> MessageResponse:
        """Create a new message"""
        message = Message(
            content=message_data.content,
            role=message_data.role,
            chat_session_id=message_data.chat_session_id
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return MessageResponse.from_orm(message)

    async def process_message(self, request: ChatMessageRequest) -> ChatMessageResponse:
        """Process a chat message with RAG functionality"""
        # Get or create chat session
        if request.chat_session_id:
            session = await self.get_session(request.chat_session_id)
            if not session:
                raise ValueError("Chat session not found")
        else:
            # Create new session
            session_data = ChatSessionCreate(
                title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                user_id=request.user_id
            )
            session = await self.create_session(session_data)

        # Create user message
        user_message_data = MessageCreate(
            content=request.message,
            role=MessageRole.USER,
            chat_session_id=session.id
        )
        user_message = await self.create_message(user_message_data)

        # TODO: Implement RAG processing here
        # For now, return a simple response
        rag_response = f"I received your message: '{request.message}'. This is a placeholder RAG response."
        
        # Create assistant message
        assistant_message_data = MessageCreate(
            content=rag_response,
            role=MessageRole.ASSISTANT,
            chat_session_id=session.id
        )
        assistant_message = await self.create_message(assistant_message_data)

        # Update session timestamp
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session.id)
            .values(updated_at=datetime.utcnow())
        )
        await self.db.commit()

        return ChatMessageResponse(
            message=assistant_message,
            chat_session=session
        )

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session (soft delete)"""
        result = await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0 