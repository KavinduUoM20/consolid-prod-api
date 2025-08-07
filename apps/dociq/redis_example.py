"""
Example of how to use Redis client in services
"""
from typing import Optional
from apps.dociq.redis_client import get_redis_client
import redis.asyncio as redis

class RedisService:
    """Example service that uses Redis for caching"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self.redis_client:
            self.redis_client = await get_redis_client()
        return self.redis_client
    
    async def cache_document_content(self, document_id: str, content: str, ttl: int = 3600):
        """Cache document content in Redis"""
        redis_client = await self.get_redis()
        key = f"document:{document_id}:content"
        await redis_client.setex(key, ttl, content)
        print(f"Cached document content for {document_id}")
    
    async def get_cached_document_content(self, document_id: str) -> Optional[str]:
        """Get cached document content from Redis"""
        redis_client = await self.get_redis()
        key = f"document:{document_id}:content"
        content = await redis_client.get(key)
        if content:
            print(f"Retrieved cached content for {document_id}")
        return content
    
    async def cache_extraction_result(self, extraction_id: str, result: dict, ttl: int = 1800):
        """Cache extraction result in Redis"""
        redis_client = await self.get_redis()
        key = f"extraction:{extraction_id}:result"
        # Convert dict to JSON string for storage
        import json
        result_json = json.dumps(result)
        await redis_client.setex(key, ttl, result_json)
        print(f"Cached extraction result for {extraction_id}")
    
    async def get_cached_extraction_result(self, extraction_id: str) -> Optional[dict]:
        """Get cached extraction result from Redis"""
        redis_client = await self.get_redis()
        key = f"extraction:{extraction_id}:result"
        result_json = await redis_client.get(key)
        if result_json:
            import json
            result = json.loads(result_json)
            print(f"Retrieved cached extraction result for {extraction_id}")
            return result
        return None
    
    async def increment_processing_counter(self, document_id: str) -> int:
        """Increment processing counter for a document"""
        redis_client = await self.get_redis()
        key = f"document:{document_id}:processing_count"
        count = await redis_client.incr(key)
        # Set expiry for the counter (24 hours)
        await redis_client.expire(key, 86400)
        return count
    
    async def get_processing_counter(self, document_id: str) -> int:
        """Get processing counter for a document"""
        redis_client = await self.get_redis()
        key = f"document:{document_id}:processing_count"
        count = await redis_client.get(key)
        return int(count) if count else 0

# Example usage in a route or service
async def example_usage():
    """Example of how to use RedisService"""
    service = RedisService()
    
    # Cache some data
    await service.cache_document_content("doc123", "This is document content")
    
    # Retrieve cached data
    content = await service.get_cached_document_content("doc123")
    print(f"Retrieved content: {content}")
    
    # Track processing attempts
    count = await service.increment_processing_counter("doc123")
    print(f"Processing count: {count}")
    
    # Cache extraction result
    result = {"status": "completed", "confidence": 0.95}
    await service.cache_extraction_result("ext456", result)
    
    # Retrieve cached result
    cached_result = await service.get_cached_extraction_result("ext456")
    print(f"Cached result: {cached_result}") 