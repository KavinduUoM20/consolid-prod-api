# api/v1/router.py
from fastapi import APIRouter
from api.v1.dociq import router as dociq_router

router = APIRouter()

# Mount tool-based or domain-based routers
router.include_router(dociq_router, prefix="/dociq")