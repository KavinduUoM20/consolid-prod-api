# api/router.py
from fastapi import APIRouter
from api.v1.router import router as v1_router

router = APIRouter()

# Mount v1 APIs
router.include_router(v1_router, prefix="/api/v1")