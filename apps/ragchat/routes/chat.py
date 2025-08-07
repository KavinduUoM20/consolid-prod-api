from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import time

from apps.ragchat.db import get_ragchat_session
from apps.ragchat.models import ChatSession, Message
from apps.ragchat.schemas.chat import (
    ChatSessionCreate, ChatSessionResponse, 
    MessageCreate, MessageResponse,
    ChatMessageRequest, ChatMessageResponse
)
from apps.ragchat.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Create a new chat session"""
    chat_service = ChatService(db)
    return await chat_service.create_session(session_data)

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    user_id: str = None,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """List all chat sessions for a user"""
    chat_service = ChatService(db)
    return await chat_service.list_sessions(user_id)

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Get a specific chat session"""
    chat_service = ChatService(db)
    session = await chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    session_id: str,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Get all messages for a chat session"""
    chat_service = ChatService(db)
    messages = await chat_service.get_messages(session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return messages

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Send a message and get RAG-powered response"""
    chat_service = ChatService(db)
    start_time = time.time()
    
    try:
        result = await chat_service.process_message(request)
        result.message.response_time = time.time() - start_time
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Delete a chat session"""
    chat_service = ChatService(db)
    success = await chat_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"message": "Chat session deleted successfully"} 