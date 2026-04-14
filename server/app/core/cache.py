from redis import Redis
from redis.exceptions import RedisError


def check_redis_connection(redis_url: str) -> bool:
    try:
        client = Redis.from_url(redis_url)
        return bool(client.ping())
    except RedisError:
        return False
