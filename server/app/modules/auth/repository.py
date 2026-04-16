from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@dataclass(slots=True)
class StoredUser:
    id: str
    email: str
    full_name: str
    password_hash: str
    role: str
    status: str

    def to_public_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
        }


class UserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_database_url(cls, database_url: str) -> "UserRepository":
        return cls(create_engine(database_url, pool_pre_ping=True))

    def get_by_email(self, email: str) -> StoredUser | None:
        query = text(
            """
            SELECT id, email, full_name, password_hash, role, status
            FROM users
            WHERE lower(email) = lower(:email)
            LIMIT 1
            """
        )
        with self._engine.connect() as connection:
            row = connection.execute(query, {"email": email}).mappings().first()
        return self._row_to_user(row)

    def get_by_id(self, user_id: str) -> StoredUser | None:
        query = text(
            """
            SELECT id, email, full_name, password_hash, role, status
            FROM users
            WHERE id = :user_id
            LIMIT 1
            """
        )
        with self._engine.connect() as connection:
            row = connection.execute(query, {"user_id": user_id}).mappings().first()
        return self._row_to_user(row)

    @staticmethod
    def _row_to_user(row: object) -> StoredUser | None:
        if row is None:
            return None

        mapping = dict(row)
        return StoredUser(
            id=str(mapping["id"]),
            email=str(mapping["email"]),
            full_name=str(mapping["full_name"]),
            password_hash=str(mapping["password_hash"]),
            role=str(mapping["role"]),
            status=str(mapping["status"]),
        )

