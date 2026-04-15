from fastapi import Header, Request

from app.core.exceptions import ApiException
from app.modules.auth.dependencies import get_auth_service


def resolve_current_user_id(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> str:
    if x_user_id:
        return x_user_id.strip()

    try:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ApiException("AUTH_UNAUTHORIZED", "Authentication is required.", status_code=401)
        user = get_auth_service().get_current_user(token)
        return user.id
    except Exception as exc:
        if isinstance(exc, ApiException):
            raise
        raise ApiException("AUTH_UNAUTHORIZED", "Authentication is required.", status_code=401) from exc
