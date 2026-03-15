"""
Event bus for asynchronous module communication
"""
import asyncio
from dataclasses import asdict
from typing import Callable, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.core.config.settings import get_settings
from app.core.infrastructure.redis_client import is_configured as redis_is_configured, publish_json, xadd_json
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("event_bus")
settings = get_settings()


class EventType(str, Enum):
    """System event types"""
    CO_GENERATED = "co_generated"
    CO_MAPPED = "co_mapped"
    EXAM_CREATED = "exam_created"
    QUESTIONS_ANALYZED = "questions_analyzed"
    MARKS_PROCESSED = "marks_processed"
    ATTAINMENT_CALCULATED = "attainment_calculated"
    REPORT_GENERATED = "report_generated"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class SystemEvent:
    """System event data structure"""
    event_type: EventType
    timestamp: datetime
    source_module: str
    data: Dict[str, Any]
    context_id: str = None  # Correlation ID for tracing


class EventBus:
    """Publish-subscribe event bus for module communication"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[SystemEvent] = []
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe handler to event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe handler from event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
    
    async def publish(self, event: SystemEvent):
        """Publish event to all subscribers"""
        self._event_history.append(event)

        handlers = self._subscribers.get(event.event_type, [])

        # Execute all handlers concurrently
        tasks = [handler(event) for handler in handlers]
        if tasks:

            # Keep handlers isolated so one exception doesn't drop all subscribers.
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Event handler failed", event_type=event.event_type, error=str(result))

        if redis_is_configured():
            payload = asdict(event)
            event_type = event.event_type.value
            channel = f"{settings.redis_stream_prefix}:events:{event_type}"
            stream = f"{settings.redis_stream_prefix}:stream:{event_type}"
            try:
                await publish_json(channel, payload)
                await xadd_json(stream, payload)
            except Exception as exc:
                logger.error("Redis event publish failed", event_type=event_type, error=str(exc))
    
    def get_event_history(self, event_type: EventType = None, limit: int = 100) -> List[SystemEvent]:
        """Get event history"""
        if event_type:
            return [e for e in self._event_history if e.event_type == event_type][-limit:]
        return self._event_history[-limit:]


# Global event bus instance
event_bus = EventBus()
