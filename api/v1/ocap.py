from fastapi import APIRouter
from apps.ocap.routes import chat

router = APIRouter()

# Include chat routes
router.include_router(chat.router, prefix="", tags=["OCAP Chat"])
