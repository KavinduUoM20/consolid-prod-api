from fastapi import APIRouter
from fastapi.responses import JSONResponse
from apps.dociq.redis_client import redis_health_check, get_redis_client

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

@router.get("/health/redis")
async def redis_health_check_endpoint():
    """Redis health check endpoint to test Redis connection"""
    try:
        # Test Redis health
        is_healthy = await redis_health_check()
        
        if is_healthy:
            # Test basic operations
            redis_client = await get_redis_client()
            await redis_client.set("health_test", "ok")
            test_value = await redis_client.get("health_test")
            await redis_client.delete("health_test")
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "service": "redis",
                    "ping": "PONG",
                    "test_operation": "successful",
                    "test_value": test_value
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "redis",
                    "error": "Redis health check failed"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "redis",
                "error": str(e)
            }
        )

@router.get("/")
async def root():
    """Root endpoint for dociq"""
    return {"message": "Dociq API is running", "endpoints": ["/hello", "/health", "/health/redis", "/extractions/"]}
