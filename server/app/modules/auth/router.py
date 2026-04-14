from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.core.exceptions import ApiException

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict[str, str]


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, object]:
    if payload.password != "quantflow-demo":
        raise ApiException("AUTH_INVALID_CREDENTIALS", "Invalid email or password.")

    response = LoginResponse(
        access_token="demo-access-token",
        refresh_token="demo-refresh-token",
        user={
            "id": "usr_admin_001",
            "email": payload.email,
            "full_name": "Alex Johnson",
            "role": "ADMIN",
        },
    )

    return {"data": response.model_dump(), "meta": {"request_id": None}, "error": None}


@router.get("/me")
def me() -> dict[str, object]:
    return {
        "data": {
            "id": "usr_admin_001",
            "email": "alex@quantflow.local",
            "full_name": "Alex Johnson",
            "role": "ADMIN",
        },
        "meta": {"request_id": None},
        "error": None,
    }
