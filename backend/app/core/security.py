from datetime import datetime, timedelta

from jose import jwt, JWTError

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )

def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError:
        return None