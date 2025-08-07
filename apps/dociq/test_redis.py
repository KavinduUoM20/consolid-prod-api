"""
Simple test script to demonstrate Redis connection
"""
import asyncio
from apps.dociq.redis_client import init_redis_connection, get_redis_client, redis_health_check

async def test_redis_connection():
    """Test Redis connection and basic operations"""
    print("🔄 Testing Redis connection...")
    
    # Initialize connection
    success = await init_redis_connection()
    if not success:
        print("❌ Failed to initialize Redis connection")
        return
    
    print("✅ Redis connection initialized successfully")
    
    # Get Redis client
    try:
        redis_client = await get_redis_client()
        print("✅ Redis client obtained successfully")
        
        # Test ping
        pong = await redis_client.ping()
        print(f"🏓 Redis ping response: {pong}")
        
        # Test basic operations
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        print(f"📝 Test set/get: {value}")
        
        # Test health check
        is_healthy = await redis_health_check()
        print(f"💚 Redis health check: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
        
        # Clean up
        await redis_client.delete("test_key")
        print("🧹 Test key cleaned up")
        
    except Exception as e:
        print(f"❌ Redis operation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_redis_connection()) 