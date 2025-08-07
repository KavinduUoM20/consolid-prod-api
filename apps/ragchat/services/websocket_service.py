from typing import Dict, List, Optional, Any
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime

class WebSocketService:
    """Service for managing WebSocket connections and real-time messaging"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, List[str]] = {}  # session_id -> [user_ids]
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
    
    async def connect_user(self, websocket: WebSocket, session_id: str, user_id: str):
        """Connect a user to a chat session"""
        await websocket.accept()
        
        # Store connection
        connection_id = f"{session_id}_{user_id}"
        self.active_connections[connection_id] = websocket
        
        # Track session connections
        if session_id not in self.session_connections:
            self.session_connections[session_id] = []
        self.session_connections[session_id].append(user_id)
        
        # Track user session
        self.user_sessions[user_id] = session_id
        
        # Send connection confirmation
        await self.send_to_user(connection_id, {
            "type": "connected",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect_user(self, session_id: str, user_id: str):
        """Disconnect a user from a chat session"""
        connection_id = f"{session_id}_{user_id}"
        
        # Remove connection
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from session tracking
        if session_id in self.session_connections:
            if user_id in self.session_connections[session_id]:
                self.session_connections[session_id].remove(user_id)
        
        # Remove user session tracking
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def send_to_user(self, connection_id: str, message: dict):
        """Send message to a specific user"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                # Connection might be closed, remove it
                del self.active_connections[connection_id]
                print(f"Error sending message to {connection_id}: {e}")
    
    async def send_to_session(self, session_id: str, message: dict):
        """Send message to all users in a session"""
        if session_id in self.session_connections:
            for user_id in self.session_connections[session_id]:
                connection_id = f"{session_id}_{user_id}"
                await self.send_to_user(connection_id, message)
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected users"""
        for connection_id in list(self.active_connections.keys()):
            await self.send_to_user(connection_id, message)
    
    def get_session_users(self, session_id: str) -> List[str]:
        """Get list of users in a session"""
        return self.session_connections.get(session_id, [])
    
    def get_user_session(self, user_id: str) -> Optional[str]:
        """Get the session a user is currently in"""
        return self.user_sessions.get(user_id)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active sessions"""
        return list(self.session_connections.keys())
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    async def send_typing_indicator(self, session_id: str, user_id: str, is_typing: bool):
        """Send typing indicator to session users"""
        message = {
            "type": "typing_indicator",
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_session(session_id, message)
    
    async def send_system_message(self, session_id: str, content: str):
        """Send system message to session users"""
        message = {
            "type": "system_message",
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_session(session_id, message)
    
    async def send_error_message(self, session_id: str, error: str):
        """Send error message to session users"""
        message = {
            "type": "error",
            "message": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_session(session_id, message) 