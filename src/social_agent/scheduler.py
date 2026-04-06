"""
Task scheduler - cron-like scheduling for automated social media operations.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A scheduled task."""

    id: str
    name: str
    func: Callable[..., Coroutine]
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    cron: str = ""  # Cron expression (e.g., "0 9 * * *")
    interval_seconds: int = 0  # Alternative: run every N seconds
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class TaskScheduler:
    """
    Simple async task scheduler.

    Supports both interval-based and cron-based scheduling.
    """

    def __init__(self, max_workers: int = 3):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._max_workers = max_workers
        self._worker_semaphore = asyncio.Semaphore(max_workers)

    def add_task(
        self,
        task_id: str,
        name: str,
        func: Callable[..., Coroutine],
        cron: str = "",
        interval_seconds: int = 0,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Add a new scheduled task."""
        if task_id in self._tasks:
            raise ValueError(f"Task '{task_id}' already exists")

        task = ScheduledTask(
            id=task_id,
            name=name,
            func=func,
            cron=cron,
            interval_seconds=interval_seconds,
            args=args,
            kwargs=kwargs or {},
        )
        self._tasks[task_id] = task
        return task

    def remove_task(self, task_id: str) -> None:
        """Remove a scheduled task."""
        self._tasks.pop(task_id, None)

    def enable_task(self, task_id: str, enabled: bool = True) -> None:
        """Enable or disable a task."""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = enabled

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "enabled": t.enabled,
                "cron": t.cron,
                "interval_seconds": t.interval_seconds,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "next_run": t.next_run.isoformat() if t.next_run else None,
                "run_count": t.run_count,
                "error_count": t.error_count,
            }
            for t in self._tasks.values()
        ]

    async def run_task(self, task: ScheduledTask) -> None:
        """Execute a single task."""
        async with self._worker_semaphore:
            try:
                logger.info(f"Running task: {task.name} (id={task.id})")
                await task.func(*task.args, **task.kwargs)
                task.run_count += 1
                task.error_count = 0
            except Exception as e:
                task.error_count += 1
                logger.error(f"Task {task.name} failed: {e}")
            finally:
                task.last_run = datetime.now()

    async def run_once(self, task_id: str) -> None:
        """Run a task immediately, ignoring schedule."""
        task = self._tasks.get(task_id)
        if task:
            await self.run_task(task)
        else:
            raise ValueError(f"Task '{task_id}' not found")

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        logger.info("Task scheduler started")

        while self._running:
            now = datetime.now()
            tasks_to_run = []

            for task in self._tasks.values():
                if not task.enabled:
                    continue

                should_run = False

                if task.interval_seconds > 0:
                    if task.last_run is None or \
                       (now - task.last_run).total_seconds() >= task.interval_seconds:
                        should_run = True

                elif task.cron and self._should_run_cron(task, now):
                    should_run = True

                if should_run:
                    task.next_run = now
                    tasks_to_run.append(task)

            # Run tasks concurrently
            if tasks_to_run:
                await asyncio.gather(
                    *[self.run_task(t) for t in tasks_to_run],
                    return_exceptions=True,
                )

            # Sleep for a short interval before checking again
            await asyncio.sleep(30)

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        logger.info("Task scheduler stopped")

    def _should_run_cron(self, task: ScheduledTask, now: datetime) -> bool:
        """Check if a cron-based task should run now."""
        if task.last_run is None:
            return True

        # Simple cron matching for common patterns
        parts = task.cron.split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron expression: {task.cron}")
            return False

        minute, hour, day, month, weekday = parts

        # Check if enough time has passed since last run (at least 1 minute)
        elapsed = (now - task.last_run).total_seconds()
        if elapsed < 60:
            return False

        # Simple matching: check hour and minute
        if hour != "*" and int(hour) != now.hour:
            return False
        if minute != "*" and int(minute) != now.minute:
            return False

        return True
