import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from ..services.manufacturing_assistant import ManufacturingTechnicalAssistant
from ..models.technical_models import WebSocketMessage
from ..config import get_ocap_settings

router = APIRouter()

# Get OCAP settings
settings = get_ocap_settings()

# Store active connections and their assistant instances
active_connections: Dict[str, Dict[str, Any]] = {}

@router.websocket("/ocap-chat/ws")
async def manufacturing_chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for manufacturing technical support chat
    """
    # Check connection limit
    if len(active_connections) >= settings.MAX_ACTIVE_CONNECTIONS:
        await websocket.close(code=1008, reason="Maximum connections reached")
        return
    
    await websocket.accept()
    
    # Generate unique connection ID
    connection_id = f"conn_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    # Initialize manufacturing assistant for this connection
    try:
        print(f"🔧 Initializing assistant for connection {connection_id}")
        assistant = ManufacturingTechnicalAssistant()
        print(f"✅ Assistant initialized successfully for {connection_id}")
    except Exception as e:
        print(f"❌ Failed to initialize assistant for {connection_id}: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        await websocket.close(code=1011, reason=f"Failed to initialize assistant: {str(e)}")
        return
    
    # Store connection and assistant
    active_connections[connection_id] = {
        "websocket": websocket,
        "assistant": assistant,
        "connected_at": datetime.now()
    }
    
    # Send welcome message
    welcome_message = WebSocketMessage(
        type="assistant_response",
        content="🔧 Welcome to Manufacturing Technical Support! I'm here to help you solve technical problems on the production floor. Please describe the issue you're experiencing.",
        timestamp=datetime.now().isoformat(),
        metadata={"connection_id": connection_id}
    )
    
    await websocket.send_text(welcome_message.json())
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse incoming message
                message_data = json.loads(data)
                user_message = message_data.get("content", data)
                
                print(f"📨 Processing message for {connection_id}: {user_message[:50]}...")
                
                # Process message through manufacturing assistant
                response = await assistant.process_user_message(user_message)
                print(f"📤 Generated response for {connection_id}: {response[:50]}...")
                
                # Get conversation summary for metadata
                summary = assistant.get_conversation_summary()
                
                # Create response message
                response_message = WebSocketMessage(
                    type="assistant_response",
                    content=response,
                    timestamp=datetime.now().isoformat(),
                    metadata={
                        "connection_id": connection_id,
                        "conversation_phase": summary.conversation_phase,
                        "turn_count": summary.turn_count,
                        "collected_slots": summary.collected_slots,
                        "missing_slots": summary.missing_slots,
                        "solved_problems": summary.solved_problems
                    }
                )
                
                # Send response back to client
                await websocket.send_text(response_message.json())
                
            except json.JSONDecodeError:
                # Handle plain text messages
                response = await assistant.process_user_message(data)
                
                response_message = WebSocketMessage(
                    type="assistant_response",
                    content=response,
                    timestamp=datetime.now().isoformat(),
                    metadata={"connection_id": connection_id}
                )
                
                await websocket.send_text(response_message.json())
                
            except Exception as e:
                # Enhanced error logging
                print(f"❌ Error processing message for {connection_id}: {str(e)}")
                print(f"❌ Error type: {type(e).__name__}")
                import traceback
                print(f"❌ Full traceback: {traceback.format_exc()}")
                
                # Send error message
                error_message = WebSocketMessage(
                    type="error",
                    content=f"I encountered an error processing your message. Please try again. Error: {str(e)}",
                    timestamp=datetime.now().isoformat(),
                    metadata={"connection_id": connection_id, "error": str(e)}
                )
                
                await websocket.send_text(error_message.json())
            
    except WebSocketDisconnect:
        print(f"🔌 Client {connection_id} disconnected")
    except Exception as e:
        print(f"❌ WebSocket error for {connection_id}: {e}")
        # Send error message if connection is still active
        try:
            error_message = WebSocketMessage(
                type="error",
                content="Connection error occurred. Please refresh and try again.",
                timestamp=datetime.now().isoformat(),
                metadata={"connection_id": connection_id, "error": str(e)}
            )
            await websocket.send_text(error_message.json())
        except:
            pass
    finally:
        # Clean up connection
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        try:
            await websocket.close()
        except:
            pass
        
        print(f"🧹 Cleaned up connection {connection_id}")

@router.get("/ocap-chat/active-connections")
async def get_active_connections():
    """Get number of active connections (for monitoring)"""
    return {
        "active_connections": len(active_connections),
        "connections": [
            {
                "connection_id": conn_id,
                "connected_at": conn_data["connected_at"].isoformat(),
                "conversation_summary": conn_data["assistant"].get_conversation_summary().dict()
            }
            for conn_id, conn_data in active_connections.items()
        ]
    }
