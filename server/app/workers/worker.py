from redis import Redis

from app.core.settings import get_settings
from app.workers.queue import BACKTEST_QUEUE_NAME


def main() -> None:
    from rq import Connection, Worker

    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    with Connection(connection):
        worker = Worker(["default", BACKTEST_QUEUE_NAME])
        worker.work()


if __name__ == "__main__":
    main()
