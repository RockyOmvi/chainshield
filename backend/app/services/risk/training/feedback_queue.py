"""
ChainShield Feedback Queue

Redis-backed queue for collecting labeled feedback from production.
Enables real-time learning from user reports and analyst reviews.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import structlog

logger = structlog.get_logger()


@dataclass
class FeedbackItem:
    """A feedback item to be processed."""
    prediction_id: str
    wallet_address: str
    original_prediction: int  # 0=legit, 1=fraud
    original_score: float
    actual_label: int  # 0=legit, 1=fraud
    feedback_source: str  # "user", "analyst", "automated"
    features: List[float]
    timestamp: str
    notes: Optional[str] = None


class FeedbackQueue:
    """
    Queue for production feedback.
    
    Supports both Redis-backed (production) and in-memory (dev) modes.
    """
    
    QUEUE_KEY = "chainshield:feedback:queue"
    PROCESSED_KEY = "chainshield:feedback:processed"
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize feedback queue.
        
        Args:
            redis_url: Redis connection URL (None for in-memory)
        """
        self.logger = logger.bind(module="feedback_queue")
        self.redis_client = None
        self.memory_queue: List[FeedbackItem] = []
        
        if redis_url:
            self._connect_redis(redis_url)
        else:
            self.logger.info("using_memory_queue")
    
    def _connect_redis(self, url: str) -> None:
        """Connect to Redis."""
        try:
            import redis
            self.redis_client = redis.from_url(url)
            self.redis_client.ping()
            self.logger.info("redis_connected")
        except Exception as e:
            self.logger.warning("redis_connection_failed", error=str(e))
            self.redis_client = None
    
    def push(self, item: FeedbackItem) -> bool:
        """
        Add feedback item to queue.
        
        Args:
            item: Feedback item to add
            
        Returns:
            True if successful
        """
        try:
            if self.redis_client:
                self.redis_client.rpush(
                    self.QUEUE_KEY,
                    json.dumps(asdict(item))
                )
            else:
                self.memory_queue.append(item)
            
            self.logger.debug(
                "feedback_pushed",
                prediction_id=item.prediction_id,
                actual=item.actual_label
            )
            return True
            
        except Exception as e:
            self.logger.error("feedback_push_failed", error=str(e))
            return False
    
    def pop(self) -> Optional[FeedbackItem]:
        """
        Pop next feedback item from queue.
        
        Returns:
            FeedbackItem or None if empty
        """
        try:
            if self.redis_client:
                data = self.redis_client.lpop(self.QUEUE_KEY)
                if data:
                    return FeedbackItem(**json.loads(data))
            else:
                if self.memory_queue:
                    return self.memory_queue.pop(0)
            
            return None
            
        except Exception as e:
            self.logger.error("feedback_pop_failed", error=str(e))
            return None
    
    def pop_batch(self, batch_size: int = 50) -> List[FeedbackItem]:
        """
        Pop multiple feedback items.
        
        Args:
            batch_size: Maximum items to pop
            
        Returns:
            List of FeedbackItems
        """
        items = []
        for _ in range(batch_size):
            item = self.pop()
            if item is None:
                break
            items.append(item)
        return items
    
    def size(self) -> int:
        """Get current queue size."""
        if self.redis_client:
            return self.redis_client.llen(self.QUEUE_KEY) or 0
        return len(self.memory_queue)
    
    def record_processed(self, item: FeedbackItem) -> None:
        """Record that an item was processed."""
        record = {
            "prediction_id": item.prediction_id,
            "processed_at": datetime.utcnow().isoformat(),
            "original": item.original_prediction,
            "actual": item.actual_label,
            "was_correct": item.original_prediction == item.actual_label,
        }
        
        if self.redis_client:
            self.redis_client.rpush(
                self.PROCESSED_KEY,
                json.dumps(record)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = {
            "queue_size": self.size(),
            "backend": "redis" if self.redis_client else "memory",
        }
        
        if self.redis_client:
            stats["processed_count"] = self.redis_client.llen(self.PROCESSED_KEY) or 0
        
        return stats


# Singleton
_feedback_queue: Optional[FeedbackQueue] = None


def get_feedback_queue() -> FeedbackQueue:
    """Get or create feedback queue singleton."""
    global _feedback_queue
    if _feedback_queue is None:
        # Use in-memory by default, Redis URL from env in production
        _feedback_queue = FeedbackQueue()
    return _feedback_queue
