from fastapi import APIRouter
from pydantic import BaseModel

from app.services.google_auth import verify_google_token

router = APIRouter()


class GoogleLoginRequest(BaseModel):
    token: str


@router.post("/google")
def google_login(payload: GoogleLoginRequest):
    user_info = verify_google_token(payload.token)

    return {
        "email": user_info["email"],
        "name": user_info["name"],
        "picture": user_info.get("picture"),
    }