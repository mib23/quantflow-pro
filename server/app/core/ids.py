from __future__ import annotations

from uuid import UUID


def coerce_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def uuid_str(value: object) -> str:
    return str(coerce_uuid(value))


def sqlite_guid(value: object) -> str:
    return coerce_uuid(value).hex

