"""
ChainShield Background Training Worker

Background worker for real-time model training from production data.
Integrates with FastAPI via startup/shutdown events.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog

logger = structlog.get_logger()


class TrainingWorker:
    """
    Background worker for incremental model training.
    
    Runs in the background and periodically:
    1. Processes feedback queue
    2. Trains model on new samples
    3. Validates and swaps model if improved
    """
    
    def __init__(
        self,
        train_interval_seconds: int = 300,  # 5 minutes
        min_samples_to_train: int = 100,
        validation_threshold: float = 0.85
    ):
        """Initialize training worker."""
        self.logger = logger.bind(module="training_worker")
        self.train_interval = train_interval_seconds
        self.min_samples = min_samples_to_train
        self.validation_threshold = validation_threshold
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_train_time: Optional[datetime] = None
        self._train_count = 0
        self._samples_processed = 0
    
    async def start(self):
        """Start the background training worker."""
        if self._running:
            self.logger.warning("worker_already_running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self.logger.info(
            "training_worker_started",
            interval=self.train_interval
        )
    
    async def stop(self):
        """Stop the background training worker."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(
            "training_worker_stopped",
            total_trains=self._train_count,
            total_samples=self._samples_processed
        )
    
    async def _run_loop(self):
        """Main training loop."""
        while self._running:
            try:
                await self._train_cycle()
            except Exception as e:
                self.logger.error("training_cycle_error", error=str(e))
            
            await asyncio.sleep(self.train_interval)
    
    async def _train_cycle(self):
        """Execute one training cycle."""
        from app.services.risk.training.feedback_queue import FeedbackQueue
        from app.services.risk.training.online_trainer import OnlineTrainer
        
        try:
            # Get feedback queue
            queue = FeedbackQueue()
            
            # Get pending samples
            samples = await queue.get_pending_samples(limit=1000)
            
            if len(samples) < self.min_samples:
                self.logger.debug(
                    "insufficient_samples",
                    count=len(samples),
                    required=self.min_samples
                )
                return
            
            self.logger.info(
                "training_started",
                samples=len(samples)
            )
            
            # Train model
            trainer = OnlineTrainer()
            
            for sample in samples:
                trainer.partial_fit(
                    features=sample["features"],
                    label=sample["label"],
                    weight=sample.get("weight", 1.0)
                )
            
            # Validate model
            validation_score = trainer.validate()
            
            if validation_score >= self.validation_threshold:
                # Swap model
                trainer.save_model()
                trainer.swap_active_model()
                
                self.logger.info(
                    "model_updated",
                    validation_score=validation_score,
                    samples=len(samples)
                )
            else:
                self.logger.warning(
                    "model_rejected",
                    validation_score=validation_score,
                    threshold=self.validation_threshold
                )
            
            # Mark samples as processed
            await queue.mark_processed([s["id"] for s in samples])
            
            self._train_count += 1
            self._samples_processed += len(samples)
            self._last_train_time = datetime.utcnow()
            
        except ImportError:
            # Modules not available in all environments
            self.logger.debug("training_modules_not_available")
        except Exception as e:
            self.logger.error("training_error", error=str(e))
    
    def get_status(self) -> dict:
        """Get worker status."""
        return {
            "running": self._running,
            "train_count": self._train_count,
            "samples_processed": self._samples_processed,
            "last_train_time": self._last_train_time.isoformat() if self._last_train_time else None,
            "train_interval_seconds": self.train_interval,
        }


# Singleton
_worker: Optional[TrainingWorker] = None


def get_training_worker() -> TrainingWorker:
    """Get training worker singleton."""
    global _worker
    if _worker is None:
        _worker = TrainingWorker()
    return _worker


# FastAPI integration
async def start_training_worker():
    """Start training worker on app startup."""
    worker = get_training_worker()
    await worker.start()


async def stop_training_worker():
    """Stop training worker on app shutdown."""
    worker = get_training_worker()
    await worker.stop()


# Scheduler for more advanced scheduling
class TrainingScheduler:
    """
    Advanced training scheduler with support for:
    - Cron-like scheduling
    - Adaptive training intervals
    - Model performance monitoring
    """
    
    def __init__(self):
        """Initialize scheduler."""
        self.logger = logger.bind(module="training_scheduler")
        self._schedules = []
        self._running = False
    
    def schedule_periodic(
        self,
        task_fn,
        interval_seconds: int,
        name: str = "periodic_task"
    ):
        """Schedule a periodic task."""
        self._schedules.append({
            "name": name,
            "fn": task_fn,
            "interval": interval_seconds,
            "last_run": None
        })
    
    async def start(self):
        """Start scheduler."""
        self._running = True
        asyncio.create_task(self._run_scheduler())
        self.logger.info("scheduler_started", tasks=len(self._schedules))
    
    async def stop(self):
        """Stop scheduler."""
        self._running = False
        self.logger.info("scheduler_stopped")
    
    async def _run_scheduler(self):
        """Run scheduler loop."""
        while self._running:
            now = datetime.utcnow()
            
            for schedule in self._schedules:
                last = schedule.get("last_run")
                interval = schedule["interval"]
                
                if last is None or (now - last).total_seconds() >= interval:
                    try:
                        if asyncio.iscoroutinefunction(schedule["fn"]):
                            await schedule["fn"]()
                        else:
                            schedule["fn"]()
                        schedule["last_run"] = now
                    except Exception as e:
                        self.logger.error(
                            "scheduled_task_error",
                            task=schedule["name"],
                            error=str(e)
                        )
            
            await asyncio.sleep(10)  # Check every 10 seconds
