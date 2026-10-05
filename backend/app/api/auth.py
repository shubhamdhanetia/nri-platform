from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.services.google_auth import verify_google_token
from app.core.security import create_access_token
from app.repositories.user_repository import (
    get_by_email,
    create_user
)

router = APIRouter()


class GoogleLoginRequest(BaseModel):
    token: str


@router.post("/google")
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    user_info = verify_google_token(payload.token)
    email = user_info["email"]
    user = get_by_email(
        db,
        email
    )

    if not user:
        user = create_user(
            db=db,
            email=email,
            name=user_info["name"],
            picture=user_info.get("picture"),
            provider_id=user_info["sub"],
        )

    access_token = create_access_token(
        user.id
    )

    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
        }
    }