import redis.asyncio as redis
import json
from typing import Any, Optional, Union
from app.core.config import settings

class RedisManager:
    def __init__(self):
        self.redis_url = settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        self.redis_client = await redis.from_url(
            self.redis_url, 
            encoding="utf-8", 
            decode_responses=True
        )
        return self.redis_client
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.redis_client:
            await self.connect()
        
        value = await self.redis_client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if not self.redis_client:
            await self.connect()
        
        if not isinstance(value, str):
            value = json.dumps(value)
        
        result = await self.redis_client.set(key, value, ex=expire)
        return result
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis_client:
            await self.connect()
        
        result = await self.redis_client.delete(key)
        return bool(result)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis_client:
            await self.connect()
        
        result = await self.redis_client.exists(key)
        return bool(result)
    
    async def cache_hash_lookup(self, hash_value: str, result: dict, expire: int = 300):
        """Cache hash lookup result for 5 minutes"""
        cache_key = f"hash_lookup:{hash_value}"
        await self.set(cache_key, result, expire)
    
    async def get_cached_hash_lookup(self, hash_value: str) -> Optional[dict]:
        """Get cached hash lookup result"""
        cache_key = f"hash_lookup:{hash_value}"
        return await self.get(cache_key)
    
    async def increment_rate_limit(self, identifier: str, window: int = 60) -> int:
        """Increment rate limit counter"""
        if not self.redis_client:
            await self.connect()
        
        key = f"rate_limit:{identifier}"
        pipe = self.redis_client.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, window)
        results = await pipe.execute()
        return results[0]

redis_manager = RedisManager()

# Dependency for FastAPI
async def get_redis():
    return redis_manager