from __future__ import annotations

import asyncio
import datetime
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

_logger = logging.getLogger("nico.scheduler")

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    _APS = True
except ModuleNotFoundError:
    _APS = False


@dataclass
class ScheduledJob:
    """Represents a job managed by the task scheduler."""

    id: str
    name: str
    trigger_type: str  # "interval" | "cron" | "date"
    trigger_args: dict[str, Any]
    action: Callable[[], Coroutine[Any, Any, None]]
    next_run_time: datetime.datetime | None = None


class TaskScheduler:
    """Manages background task scheduling, reminders, and periodic jobs.

    Delegates to ``apscheduler.schedulers.asyncio.AsyncIOScheduler`` if available,
    otherwise implements a fallback loop using native ``asyncio``.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._scheduler: Any | None = None
        self._fallback_task: asyncio.Task | None = None

        if _APS:
            self._scheduler = AsyncIOScheduler()
        else:
            _logger.info("APScheduler not available, using native asyncio loop fallback.")

    async def start(self) -> None:
        """Start the scheduler background worker/service."""
        if self._running:
            return

        self._running = True
        if self._scheduler:
            self._scheduler.start()
        else:
            self._fallback_task = asyncio.create_task(self._fallback_loop())
        _logger.info("TaskScheduler service started.")

    async def stop(self) -> None:
        """Shutdown the scheduler cleanly."""
        if not self._running:
            return

        self._running = False
        if self._scheduler:
            self._scheduler.shutdown()
        if self._fallback_task:
            self._fallback_task.cancel()
            try:
                await self._fallback_task
            except asyncio.CancelledError:
                pass
        _logger.info("TaskScheduler service stopped.")

    # ------------------------------------------------------------------
    # Job Scheduling API
    # ------------------------------------------------------------------

    def add_job(
        self,
        name: str,
        trigger_type: str,
        trigger_args: dict[str, Any],
        action: Callable[[], Coroutine[Any, Any, None]],
    ) -> str:
        """Add a job to run periodically or at a specific time.

        Args:
            name:         Descriptive name for logging and list views.
            trigger_type: "interval" (seconds) or "date" (run once) or "cron" (string cron expression).
            trigger_args: Keyword args for the trigger (e.g. ``{"seconds": 10}`` or ``{"run_date": ...}``).
            action:       Async function/coroutine to execute.

        Returns:
            Unique string job ID.
        """
        job_id = str(uuid.uuid4())
        
        # Calculate next run time (basic fallback logic)
        next_run = None
        if trigger_type == "date":
            raw = trigger_args.get("run_date")
            if isinstance(raw, str):
                try:
                    next_run = datetime.datetime.fromisoformat(raw)
                except ValueError:
                    next_run = None
            else:
                next_run = raw
        elif trigger_type == "interval":
            seconds = trigger_args.get("seconds", 60)
            next_run = datetime.datetime.now() + datetime.timedelta(seconds=seconds)

        job = ScheduledJob(
            id=job_id,
            name=name,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            action=action,
            next_run_time=next_run,
        )
        self._jobs[job_id] = job

        if self._scheduler:
            # Map NICO parameters to APScheduler job options
            if trigger_type == "interval":
                self._scheduler.add_job(
                    action, "interval", id=job_id, name=name, **trigger_args
                )
            elif trigger_type == "cron":
                self._scheduler.add_job(
                    action, "cron", id=job_id, name=name, **trigger_args
                )
            elif trigger_type == "date":
                self._scheduler.add_job(
                    action, "date", id=job_id, name=name, **trigger_args
                )
        
        _logger.info("Added job id=%s name='%s' trigger=%s", job_id, name, trigger_type)
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Cancel/remove a scheduled job."""
        if job_id not in self._jobs:
            return False

        self._jobs.pop(job_id)
        if self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
        
        _logger.info("Removed job id=%s", job_id)
        return True

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return all active scheduled jobs with metadata."""
        results = []
        for j_id, job in self._jobs.items():
            next_run = job.next_run_time
            if self._scheduler:
                aps_job = self._scheduler.get_job(j_id)
                if aps_job:
                    next_run = aps_job.next_run_time
            
            results.append({
                "id": j_id,
                "name": job.name,
                "trigger_type": job.trigger_type,
                "trigger_args": job.trigger_args,
                "next_run_time": next_run.isoformat() if next_run else None,
            })
        return results

    # ------------------------------------------------------------------
    # Native asyncio fallback engine
    # ------------------------------------------------------------------

    async def _fallback_loop(self) -> None:
        """Basic event loop processing interval/date triggers when APScheduler is missing."""
        while self._running:
            await asyncio.sleep(1.0)
            now = datetime.datetime.now()

            # Execute due jobs
            to_remove = []
            for j_id, job in list(self._jobs.items()):
                if job.next_run_time and now >= job.next_run_time:
                    # Dispatch task
                    asyncio.create_task(self._run_job_safely(job))

                    if job.trigger_type == "date":
                        to_remove.append(j_id)
                    elif job.trigger_type == "interval":
                        seconds = job.trigger_args.get("seconds", 60)
                        job.next_run_time = now + datetime.timedelta(seconds=seconds)

            for j_id in to_remove:
                self.remove_job(j_id)

    async def _run_job_safely(self, job: ScheduledJob) -> None:
        try:
            await job.action()
            # Publish event if success
            try:
                from nico.events import NicoEvent, publish
                @dataclass
                class BackgroundJobExecuted(NicoEvent):
                    job_name: str
                    success: bool
                await publish(BackgroundJobExecuted(job_name=job.name, success=True))
            except Exception:
                pass
        except Exception as exc:
            _logger.exception("Error executing background job id=%s name='%s': %s", job.id, job.name, exc)
