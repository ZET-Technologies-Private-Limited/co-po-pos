"""
Multi-tier caching service with Redis and in-memory layers
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar
from app.core.infrastructure.redis_client import get_cache, set_cache
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("multi_tier_cache")

T = TypeVar('T')

# In-memory cache (L1)
_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_stats = {"hits": 0, "misses": 0, "redis_hits": 0, "redis_misses": 0}


class CacheEntry:
    def __init__(self, value: Any, timestamp: float, ttl: int):
        self.value = value
        self.timestamp = timestamp
        self.ttl = ttl
        self.expires_at = timestamp + ttl
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def is_stale(self, fresh_ttl: int) -> bool:
        return time.time() > (self.timestamp + fresh_ttl)


async def get_or_compute(
    key: str,
    compute_fn: Callable[[], Any],
    fresh_ttl: int = 300,  # 5 minutes fresh
    stale_ttl: int = 3600,  # 1 hour stale
    memory_ttl: int = 60,   # 1 minute in memory
) -> Tuple[Any, str]:
    """
    Multi-tier cache with fresh/stale semantics:
    1. Check memory cache (L1)
    2. Check Redis cache (L2) 
    3. Compute if needed
    
    Returns: (value, source) where source is "memory", "redis", or "computed"
    """
    now = time.time()
    
    # L1: Memory cache check
    if key in _memory_cache:
        entry = _memory_cache[key]
        if not entry.is_expired():
            _cache_stats["hits"] += 1
            return entry.value, "memory"
        else:
            del _memory_cache[key]
    
    # L2: Redis cache check
    try:
        cached_data = await get_cache(f"cache:{key}")
        if cached_data and isinstance(cached_data, dict):
            timestamp = cached_data.get("timestamp", 0)
            value = cached_data.get("value")
            
            if value is not None and (now - timestamp) < stale_ttl:
                # Store in memory cache
                _memory_cache[key] = CacheEntry(value, timestamp, memory_ttl)
                _cache_stats["redis_hits"] += 1
                
                # Return stale data if not fresh
                if (now - timestamp) < fresh_ttl:
                    return value, "redis"
                else:
                    # Trigger background refresh for stale data
                    asyncio.create_task(_background_refresh(key, compute_fn, fresh_ttl, stale_ttl))
                    return value, "redis-stale"
    except Exception as e:
        logger.warning(f"Redis cache error for key {key}: {e}")
    
    # L3: Compute fresh value
    _cache_stats["misses"] += 1
    try:
        if asyncio.iscoroutinefunction(compute_fn):
            value = await compute_fn()
        else:
            value = compute_fn()
        
        # Store in both caches
        await _store_in_caches(key, value, fresh_ttl, stale_ttl, memory_ttl)
        return value, "computed"
    
    except Exception as e:
        logger.error(f"Compute function failed for key {key}: {e}")
        raise


async def _background_refresh(
    key: str,
    compute_fn: Callable[[], Any],
    fresh_ttl: int,
    stale_ttl: int
):
    """Refresh stale cache entry in background"""
    try:
        if asyncio.iscoroutinefunction(compute_fn):
            value = await compute_fn()
        else:
            value = compute_fn()
        
        await _store_in_caches(key, value, fresh_ttl, stale_ttl, 60)
        logger.debug(f"Background refresh completed for key {key}")
    except Exception as e:
        logger.error(f"Background refresh failed for key {key}: {e}")


async def _store_in_caches(
    key: str,
    value: Any,
    fresh_ttl: int,
    stale_ttl: int,
    memory_ttl: int
):
    """Store value in both memory and Redis caches"""
    now = time.time()
    
    # Store in memory cache
    _memory_cache[key] = CacheEntry(value, now, memory_ttl)
    
    # Store in Redis cache
    cache_data = {
        "value": value,
        "timestamp": now,
        "fresh_ttl": fresh_ttl,
        "stale_ttl": stale_ttl
    }
    await set_cache(f"cache:{key}", cache_data, stale_ttl)


async def invalidate_cache(key: str) -> bool:
    """Invalidate cache entry from all tiers"""
    # Remove from memory
    if key in _memory_cache:
        del _memory_cache[key]
    
    # Remove from Redis
    from app.core.infrastructure.redis_client import delete_key
    return await delete_key(f"cache:{key}")


async def invalidate_pattern(pattern: str) -> int:
    """Invalidate all cache entries matching pattern (memory + Redis). Returns total invalidated."""
    count = 0
    # Memory cache
    keys_to_remove = [k for k in _memory_cache.keys() if pattern in k]
    for key in keys_to_remove:
        del _memory_cache[key]
        count += 1
    # Redis: multi_tier_cache stores under "cache:{key}"
    from app.core.infrastructure.redis_client import delete_keys_matching_pattern
    redis_pattern = f"cache:{pattern}*" if "*" not in pattern else f"cache:{pattern}"
    redis_deleted = await delete_keys_matching_pattern(redis_pattern)
    count += redis_deleted
    if count:
        logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
    return count


async def invalidate_course_report_cache(course_id: str) -> bool:
    """Invalidate report and visualization cache for a course (real-time update after marks/CO/exam changes)."""
    await invalidate_cache(f"report_payload:{course_id}")
    return True


async def invalidate_exam_preview_cache(exam_id: str) -> int:
    """Invalidate CO preview cache for an exam (all threshold variants). Returns count invalidated."""
    return await invalidate_pattern(f"co_preview:{exam_id}:")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache performance statistics"""
    total_requests = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "memory_cache_size": len(_memory_cache),
        "total_requests": total_requests,
        "memory_hits": _cache_stats["hits"],
        "redis_hits": _cache_stats["redis_hits"],
        "misses": _cache_stats["misses"],
        "hit_rate_percent": round(hit_rate, 2),
        "stats": _cache_stats
    }


def clear_memory_cache():
    """Clear all memory cache entries"""
    global _memory_cache
    _memory_cache.clear()
    logger.info("Memory cache cleared")


# Cleanup expired entries periodically
async def cleanup_expired_entries():
    """Remove expired entries from memory cache"""
    expired_keys = [
        key for key, entry in _memory_cache.items()
        if entry.is_expired()
    ]
    
    for key in expired_keys:
        del _memory_cache[key]
    
    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")