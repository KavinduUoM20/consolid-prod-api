# api/v1/router.py
from fastapi import APIRouter
from api.v1.dociq import router as dociq_router
from api.v1.ocap import router as ocap_router
from core.auth.routes import router as auth_router

router = APIRouter()

# Mount authentication router
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Mount tool-based or domain-based routers
router.include_router(dociq_router, prefix="/dociq")
router.include_router(ocap_router, prefix="/ocap")