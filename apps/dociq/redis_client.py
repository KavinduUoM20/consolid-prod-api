import redis.asyncio as redis
from apps.dociq.config import get_dociq_settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

settings = get_dociq_settings()

# Create Redis client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    socket_timeout=settings.REDIS_TIMEOUT / 1000,  # Convert ms to seconds
    socket_connect_timeout=settings.REDIS_TIMEOUT / 1000,
    retry_on_timeout=True,
    health_check_interval=30,
    decode_responses=True  # Automatically decode responses to strings
)

async def init_redis_connection():
    """Initialize Redis connection and test connectivity"""
    try:
        # Test the connection
        pong = await redis_client.ping()
        logger.info(f"Redis connection successful: {pong}")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False

async def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    try:
        # Test connection before returning
        await redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error(f"Redis client error: {e}")
        raise

async def close_redis_connection():
    """Close Redis connection"""
    try:
        await redis_client.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")

# Event handlers for connection management
@redis_client.on_connect
async def on_connect():
    logger.info("Connected to Redis")

@redis_client.on_disconnect
async def on_disconnect():
    logger.warning("Disconnected from Redis")

# Health check function
async def redis_health_check() -> bool:
    """Check if Redis is healthy and responding"""
    try:
        pong = await redis_client.ping()
        return pong == "PONG"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False 