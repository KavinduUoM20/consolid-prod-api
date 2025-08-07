from fastapi import APIRouter
from apps.ragchat.routes import chat, documents, websocket

router = APIRouter()

# Include chat routes
router.include_router(chat.router, prefix="", tags=["Chat"])

# Include document routes
router.include_router(documents.router, prefix="", tags=["Documents"])

# Include WebSocket routes
router.include_router(websocket.router, prefix="", tags=["WebSocket"]) 