from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def create_sync_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def check_database_connection(database_url: str) -> bool:
    try:
        engine = create_sync_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
