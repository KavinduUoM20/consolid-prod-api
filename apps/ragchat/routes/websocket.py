from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional
import json
import time
from datetime import datetime

from apps.ragchat.db import get_ragchat_session
from apps.ragchat.models import ChatSession, Message
from apps.ragchat.schemas.chat import (
    ChatSessionCreate, ChatSessionResponse, 
    MessageCreate, MessageResponse,
    ChatMessageRequest, ChatMessageResponse
)
from apps.ragchat.services.chat_service import ChatService
from apps.ragchat.services.websocket_service import WebSocketService

router = APIRouter()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time RAG chat"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process the message
            response = await process_websocket_message(session_id, message_data)
            
            # Send response back to client
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        error_response = {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_response))
        manager.disconnect(session_id)

async def process_websocket_message(session_id: str, message_data: dict):
    """Process incoming WebSocket message"""
    message_type = message_data.get("type", "message")
    
    if message_type == "message":
        return await handle_chat_message(session_id, message_data)
    elif message_type == "join_session":
        return await handle_join_session(session_id, message_data)
    elif message_type == "leave_session":
        return await handle_leave_session(session_id, message_data)
    else:
        return {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        }

async def handle_chat_message(session_id: str, message_data: dict):
    """Handle chat message via WebSocket"""
    try:
        # Get database session
        from apps.ragchat.db import get_ragchat_session
        db = await anext(get_ragchat_session())
        
        chat_service = ChatService(db)
        
        # Create chat message request
        request = ChatMessageRequest(
            message=message_data.get("content", ""),
            chat_session_id=session_id,
            user_id=message_data.get("user_id")
        )
        
        # Process message
        start_time = time.time()
        result = await chat_service.process_message(request)
        response_time = time.time() - start_time
        
        # Prepare WebSocket response
        response = {
            "type": "message",
            "message": {
                "id": result.message.id,
                "content": result.message.content,
                "role": result.message.role.value,
                "created_at": result.message.created_at.isoformat(),
                "chat_session_id": result.message.chat_session_id,
                "sources": result.message.sources,
                "tokens_used": result.message.tokens_used,
                "response_time": response_time
            },
            "session": {
                "id": result.chat_session.id,
                "title": result.chat_session.title,
                "description": result.chat_session.description,
                "created_at": result.chat_session.created_at.isoformat(),
                "updated_at": result.chat_session.updated_at.isoformat(),
                "is_active": result.chat_session.is_active,
                "user_id": result.chat_session.user_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
        
    except Exception as e:
        return {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def handle_join_session(session_id: str, message_data: dict):
    """Handle join session message"""
    try:
        # Get database session
        from apps.ragchat.db import get_ragchat_session
        db = await anext(get_ragchat_session())
        
        chat_service = ChatService(db)
        
        # Get session info
        session = await chat_service.get_session(session_id)
        if not session:
            return {
                "type": "error",
                "message": "Chat session not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get recent messages
        messages = await chat_service.get_messages(session_id)
        
        response = {
            "type": "session_joined",
            "session": {
                "id": session.id,
                "title": session.title,
                "description": session.description,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "is_active": session.is_active,
                "user_id": session.user_id
            },
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "role": msg.role.value,
                    "created_at": msg.created_at.isoformat(),
                    "chat_session_id": msg.chat_session_id,
                    "sources": msg.sources,
                    "tokens_used": msg.tokens_used,
                    "response_time": msg.response_time
                } for msg in messages
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
        
    except Exception as e:
        return {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def handle_leave_session(session_id: str, message_data: dict):
    """Handle leave session message"""
    manager.disconnect(session_id)
    
    return {
        "type": "session_left",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    } 