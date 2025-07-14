from fastapi import APIRouter
from apps.dociq.routes import hello, template, extraction

router = APIRouter()

# Include hello route(s) from dociq app
router.include_router(hello.router, prefix="", tags=["Hello"])

# Include template routes
router.include_router(template.router, prefix="", tags=["Templates"])
router.include_router(extraction.router, prefix="", tags=["Extractions"])