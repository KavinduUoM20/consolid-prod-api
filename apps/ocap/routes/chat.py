from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ocap-chat/ws")
async def extraction_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time extraction updates
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Echo back the same message (simple response)
            await websocket.send_text(f"Echo: {data}")
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
