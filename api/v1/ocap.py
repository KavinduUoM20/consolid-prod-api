from fastapi import APIRouter
from apps.ocap.routes import chat, health

router = APIRouter()

# Include chat routes
router.include_router(chat.router, prefix="", tags=["OCAP Chat"])

# Include health check routes
router.include_router(health.router, prefix="", tags=["OCAP Health"])
