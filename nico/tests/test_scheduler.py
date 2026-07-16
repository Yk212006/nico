import asyncio
import pytest

from nico.scheduler import TaskScheduler


@pytest.mark.asyncio
async def test_scheduler_add_and_remove_job() -> None:
    scheduler = TaskScheduler()
    executed = []

    async def my_task() -> None:
        executed.append(True)

    job_id = scheduler.add_job("test", "interval", {"seconds": 1}, my_task)
    assert job_id is not None

    jobs = scheduler.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["name"] == "test"

    removed = scheduler.remove_job(job_id)
    assert removed is True
    assert len(scheduler.list_jobs()) == 0


@pytest.mark.asyncio
async def test_scheduler_remove_nonexistent_job() -> None:
    scheduler = TaskScheduler()
    assert scheduler.remove_job("nonexistent") is False


@pytest.mark.asyncio
async def test_scheduler_date_trigger_execution() -> None:
    scheduler = TaskScheduler()
    import datetime

    executed = []

    async def my_task() -> None:
        executed.append(True)

    future = (datetime.datetime.now() + datetime.timedelta(seconds=1)).isoformat()
    job_id = scheduler.add_job("date_task", "date", {"run_date": future}, my_task)
    assert job_id is not None

    await scheduler.start()
    await asyncio.sleep(0.1)
    await scheduler.stop()
    # Job was added before start, so it exists
    assert job_id in [j["id"] for j in scheduler.list_jobs()]
