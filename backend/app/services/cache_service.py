# app/services/cache_service.py
import redis
import json
from typing import Any, Optional
from app.config import settings

class CacheService:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}. Using in-memory cache.")
            self.redis_client = None
            self._memory_cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                return self._memory_cache.get(key)
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        try:
            if self.redis_client:
                if ttl:
                    return self.redis_client.setex(key, ttl, json.dumps(value))
                else:
                    return self.redis_client.set(key, json.dumps(value))
            else:
                self._memory_cache[key] = value
                return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                self._memory_cache.pop(key, None)
                return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.flushdb())
            else:
                self._memory_cache.clear()
                return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
