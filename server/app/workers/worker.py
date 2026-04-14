from redis import Redis
from rq import Connection, Worker

from app.core.settings import get_settings


def main() -> None:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    with Connection(connection):
        worker = Worker(["default"])
        worker.work()


if __name__ == "__main__":
    main()
