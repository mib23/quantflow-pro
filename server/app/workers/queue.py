from typing import TYPE_CHECKING, Any

from redis import Redis

from app.core.settings import get_settings

BACKTEST_QUEUE_NAME = "backtests"

if TYPE_CHECKING:
    from rq import Queue


def get_queue(name: str = "default") -> "Queue":
    from rq import Queue

    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    return Queue(name=name, connection=connection)


def enqueue_backtest_job(job_id: str, *, database_url: str | None = None) -> str:
    queue = get_queue(BACKTEST_QUEUE_NAME)
    rq_job = queue.enqueue("app.modules.backtests.executor.execute_backtest_job", job_id=job_id, database_url=database_url)
    return rq_job.get_id()
