from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello from Dociq!"}

@router.get("/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "dociq-api",
            "version": "1.0.0"
        }
    )

@router.get("/")
async def root():
    """Root endpoint for dociq"""
    return {"message": "Dociq API is running", "endpoints": ["/hello", "/health", "/extractions/"]}
