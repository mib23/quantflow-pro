from app.core.database import check_database_connection


def test_database_connection_with_sqlite_memory() -> None:
    assert check_database_connection("sqlite+pysqlite:///:memory:") is True
