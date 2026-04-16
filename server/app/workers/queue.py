from redis import Redis
from rq import Queue

from app.core.settings import get_settings


def get_queue(name: str = "default") -> Queue:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    return Queue(name=name, connection=connection)
