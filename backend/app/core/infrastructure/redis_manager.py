"""
Redis Cache Manager
Implements all cache patterns and TTLs from specification
"""
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("redis_cache")

class RedisManager:
    """Production Redis cache and pub/sub manager"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_pool = None
        self.pubsub = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        if self._initialized:
            return
        
        try:
            redis_url = getattr(self.settings, 'redis_url', 'redis://localhost:6379/0')
            self.redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True
            )
            
            # Test connection
            async with redis.Redis(connection_pool=self.redis_pool) as r:
                await r.ping()
            
            self._initialized = True
            logger.info("Redis connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            raise
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis client from pool"""
        if not self._initialized:
            await self.initialize()
        return redis.Redis(connection_pool=self.redis_pool)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CACHE OPERATIONS - All patterns from specification
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def set_session(self, user_id: str, session_data: Dict[str, Any], ttl: int = 1800):
        """Cache user session data - TTL: 30 min"""
        async with await self.get_redis() as r:
            key = f"session:{user_id}"
            await r.setex(key, ttl, json.dumps(session_data))
            logger.debug(f"Session cached for user {user_id}")
    
    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data"""
        async with await self.get_redis() as r:
            key = f"session:{user_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
    
    async def blacklist_jwt(self, jti: str, exp_timestamp: int):
        """Blacklist JWT token until expiry"""
        async with await self.get_redis() as r:
            key = f"jwt_blacklist:{jti}"
            ttl = max(1, exp_timestamp - int(datetime.utcnow().timestamp()))
            await r.setex(key, ttl, "1")
            logger.debug(f"JWT {jti} blacklisted for {ttl}s")
    
    async def is_jwt_blacklisted(self, jti: str) -> bool:
        """Check if JWT is blacklisted"""
        async with await self.get_redis() as r:
            key = f"jwt_blacklist:{jti}"
            return await r.exists(key) > 0
    
    async def set_co_preview(self, exam_id: str, preview_data: Dict[str, Any], ttl: int = 300):
        """Cache CO attainment preview - TTL: 5 min"""
        async with await self.get_redis() as r:
            key = f"co_preview:{exam_id}"
            await r.setex(key, ttl, json.dumps(preview_data))
    
    async def get_co_preview(self, exam_id: str) -> Optional[Dict[str, Any]]:
        """Get CO attainment preview"""
        async with await self.get_redis() as r:
            key = f"co_preview:{exam_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
    
    async def set_po_attainment(self, dept_id: str, ay_id: str, attainment_data: Dict[str, Any], ttl: int = 3600):
        """Cache PO attainment data - TTL: 1 hr"""
        async with await self.get_redis() as r:
            key = f"po_attainment:{dept_id}:{ay_id}"
            await r.setex(key, ttl, json.dumps(attainment_data))
    
    async def get_po_attainment(self, dept_id: str, ay_id: str) -> Optional[Dict[str, Any]]:
        """Get PO attainment data"""
        async with await self.get_redis() as r:
            key = f"po_attainment:{dept_id}:{ay_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
    
    async def set_report_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
        """Cache report generation job status - TTL: 24 hr"""
        async with await self.get_redis() as r:
            key = f"report_job:{job_id}"
            await r.setex(key, ttl, json.dumps(job_data))
    
    async def get_report_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get report job status"""
        async with await self.get_redis() as r:
            key = f"report_job:{job_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
    
    async def update_report_job(self, job_id: str, updates: Dict[str, Any]):
        """Update report job status"""
        async with await self.get_redis() as r:
            key = f"report_job:{job_id}"
            existing = await r.get(key)
            if existing:
                data = json.loads(existing)
                data.update(updates)
                ttl = await r.ttl(key)
                if ttl > 0:
                    await r.setex(key, ttl, json.dumps(data))
    
    async def lock_marks(self, exam_id: str, ttl: int = 3600):
        """Lock marks editing - TTL: until unlock"""
        async with await self.get_redis() as r:
            key = f"marks_lock:{exam_id}"
            await r.setex(key, ttl, "1")
            logger.info(f"Marks locked for exam {exam_id}")
    
    async def unlock_marks(self, exam_id: str):
        """Unlock marks editing"""
        async with await self.get_redis() as r:
            key = f"marks_lock:{exam_id}"
            await r.delete(key)
            logger.info(f"Marks unlocked for exam {exam_id}")
    
    async def is_marks_locked(self, exam_id: str) -> bool:
        """Check if marks are locked"""
        async with await self.get_redis() as r:
            key = f"marks_lock:{exam_id}"
            return await r.exists(key) > 0
    
    async def check_rate_limit(self, user_id: str, endpoint: str, limit: int = 60, window: int = 60) -> bool:
        """Rate limiting - TTL: 1 min"""
        async with await self.get_redis() as r:
            key = f"rate_limit:{user_id}:{endpoint}"
            current = await r.get(key)
            
            if current is None:
                await r.setex(key, window, "1")
                return True
            
            count = int(current)
            if count >= limit:
                return False
            
            await r.incr(key)
            return True
    
    async def set_co_library(self, course_code: str, regulation: str, cos_data: List[Dict], ttl: int = 86400):
        """Cache default CO templates - TTL: 24 hr"""
        async with await self.get_redis() as r:
            key = f"co_library:{course_code}:{regulation}"
            await r.setex(key, ttl, json.dumps(cos_data))
    
    async def get_co_library(self, course_code: str, regulation: str) -> Optional[List[Dict]]:
        """Get default CO templates"""
        async with await self.get_redis() as r:
            key = f"co_library:{course_code}:{regulation}"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUB/SUB EVENT SYSTEM - All channels from specification
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def publish_event(self, channel: str, payload: Dict[str, Any]):
        """Publish event to Redis pub/sub channel"""
        async with await self.get_redis() as r:
            message = json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload
            })
            await r.publish(channel, message)
            logger.info(f"Event published to {channel}")
    
    async def subscribe_to_events(self, channels: List[str], callback):
        """Subscribe to Redis pub/sub channels"""
        async with await self.get_redis() as r:
            pubsub = r.pubsub()
            await pubsub.subscribe(*channels)
            
            try:
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            await callback(message['channel'], data)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
            finally:
                await pubsub.unsubscribe(*channels)
    
    # Event publishing helpers
    async def publish_marks_uploaded(self, exam_id: str, faculty_id: str, lead_id: str):
        """Publish marks.uploaded event"""
        await self.publish_event("marks.uploaded", {
            "exam_id": exam_id,
            "faculty_id": faculty_id,
            "lead_id": lead_id
        })
    
    async def publish_marks_approved(self, exam_id: str, course_id: str):
        """Publish marks.approved event"""
        await self.publish_event("marks.approved", {
            "exam_id": exam_id,
            "course_id": course_id
        })
    
    async def publish_attainment_computed(self, course_id: str, co_results: List[Dict]):
        """Publish attainment.computed event"""
        await self.publish_event("attainment.computed", {
            "course_id": course_id,
            "co_results": co_results
        })
    
    async def publish_level1_co_detected(self, co_id: str, course_id: str, user_ids: List[str]):
        """Publish level1_co.detected event"""
        await self.publish_event("level1_co.detected", {
            "co_id": co_id,
            "course_id": course_id,
            "user_ids": user_ids
        })
    
    async def publish_report_ready(self, job_id: str, user_id: str, url: str):
        """Publish report.ready event"""
        await self.publish_event("report.ready", {
            "job_id": job_id,
            "user_id": user_id,
            "url": url
        })
    
    async def publish_ay_locked(self, ay_id: str):
        """Publish ay.locked event"""
        await self.publish_event("ay.locked", {
            "ay_id": ay_id
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CACHE INVALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        async with await self.get_redis() as r:
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)
                logger.info(f"Invalidated {len(keys)} keys matching {pattern}")
    
    async def invalidate_course_cache(self, course_id: str):
        """Invalidate all cache entries for a course"""
        patterns = [
            f"co_preview:*{course_id}*",
            f"po_attainment:*{course_id}*",
            f"report_job:*{course_id}*"
        ]
        for pattern in patterns:
            await self.invalidate_pattern(pattern)
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        patterns = [
            f"session:{user_id}",
            f"rate_limit:{user_id}:*"
        ]
        for pattern in patterns:
            await self.invalidate_pattern(pattern)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            async with await self.get_redis() as r:
                start_time = datetime.utcnow()
                await r.ping()
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                info = await r.info()
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "redis_version": info.get("redis_version", "unknown")
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def close(self):
        """Close Redis connections"""
        if self.redis_pool:
            await self.redis_pool.disconnect()
            logger.info("Redis connections closed")

# Global Redis manager instance
redis_manager = RedisManager()

# Convenience functions for common operations
async def cache_set(key: str, value: Any, ttl: int = 3600):
    """Set cache value with TTL"""
    async with await redis_manager.get_redis() as r:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await r.setex(key, ttl, value)

async def cache_get(key: str) -> Optional[Any]:
    """Get cache value"""
    async with await redis_manager.get_redis() as r:
        data = await r.get(key)
        if data:
            try:
                return json.loads(data)
            except:
                return data
        return None

async def cache_delete(key: str):
    """Delete cache key"""
    async with await redis_manager.get_redis() as r:
        await r.delete(key)

async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    async with await redis_manager.get_redis() as r:
        return await r.exists(key) > 0