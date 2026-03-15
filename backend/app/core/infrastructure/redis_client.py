"""
Redis client for caching and session management
"""
import json
import redis.asyncio as redis
from typing import Any, Dict, Optional, Union
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("redis_client")
settings = get_settings()

# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


def is_configured() -> bool:
    """Return whether Redis configuration is available."""
    return bool(getattr(settings, "redis_url", None))


async def get_redis_client() -> redis.Redis:
    """Get Redis client with connection pooling"""
    global _redis_pool, _redis_client
    
    if _redis_client is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True
            )
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    return _redis_client


async def ping_redis() -> bool:
    """Check Redis connectivity"""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return False


async def set_json(key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
    """Store JSON data in Redis"""
    try:
        client = await get_redis_client()
        json_str = json.dumps(value, default=str)
        if ttl_seconds:
            await client.setex(key, ttl_seconds, json_str)
        else:
            await client.set(key, json_str)
        return True
    except Exception as e:
        logger.error(f"Redis set_json failed for key {key}: {e}")
        return False


async def get_json(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve JSON data from Redis"""
    try:
        client = await get_redis_client()
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Redis get_json failed for key {key}: {e}")
        return None


async def delete_key(key: str) -> bool:
    """Delete key from Redis"""
    try:
        client = await get_redis_client()
        result = await client.delete(key)
        return result > 0
    except Exception as e:
        logger.error(f"Redis delete failed for key {key}: {e}")
        return False


async def delete_keys_matching_pattern(pattern: str) -> int:
    """Delete all Redis keys matching pattern (e.g. 'cache:co_preview:exam123:*'). Returns count deleted."""
    try:
        client = await get_redis_client()
        count = 0
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
                count += len(keys)
            if cursor == 0:
                break
        if count:
            logger.debug(f"Invalidated {count} Redis keys matching {pattern}")
        return count
    except Exception as e:
        logger.error(f"Redis delete pattern failed for {pattern}: {e}")
        return 0


async def set_cache(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Set cache value with TTL"""
    try:
        client = await get_redis_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        await client.setex(key, ttl_seconds, value)
        return True
    except Exception as e:
        logger.error(f"Redis cache set failed for key {key}: {e}")
        return False


async def get_cache(key: str) -> Optional[Any]:
    """Get cache value"""
    try:
        client = await get_redis_client()
        value = await client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    except Exception as e:
        logger.error(f"Redis cache get failed for key {key}: {e}")
        return None


async def increment_counter(key: str, ttl_seconds: Optional[int] = None) -> int:
    """Increment counter with optional TTL"""
    try:
        client = await get_redis_client()
        count = await client.incr(key)
        if ttl_seconds and count == 1:  # Set TTL only on first increment
            await client.expire(key, ttl_seconds)
        return count
    except Exception as e:
        logger.error(f"Redis increment failed for key {key}: {e}")
        return 0


async def publish_json(channel: str, payload: Dict[str, Any]) -> bool:
    """Publish a JSON payload to a Redis pub/sub channel."""
    try:
        client = await get_redis_client()
        await client.publish(channel, json.dumps(payload, default=str))
        return True
    except Exception as e:
        logger.error(f"Redis publish_json failed for channel {channel}: {e}")
        return False


async def xadd_json(stream: str, payload: Dict[str, Any], maxlen: Optional[int] = None) -> bool:
    """Append a JSON payload to a Redis stream."""
    try:
        client = await get_redis_client()
        fields = {"payload": json.dumps(payload, default=str)}
        kwargs = {"maxlen": maxlen, "approximate": True} if maxlen else {}
        await client.xadd(stream, fields, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Redis xadd_json failed for stream {stream}: {e}")
        return False


async def add_to_set(key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
    """Add value to Redis set"""
    try:
        client = await get_redis_client()
        await client.sadd(key, value)
        if ttl_seconds:
            await client.expire(key, ttl_seconds)
        return True
    except Exception as e:
        logger.error(f"Redis set add failed for key {key}: {e}")
        return False


async def get_set_members(key: str) -> set:
    """Get all members of Redis set"""
    try:
        client = await get_redis_client()
        members = await client.smembers(key)
        return members
    except Exception as e:
        logger.error(f"Redis set get failed for key {key}: {e}")
        return set()


async def close_redis_client():
    """Close Redis connection"""
    global _redis_client, _redis_pool
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
    logger.info("Redis client closed")