from sqlalchemy.orm import Session

from app.models.user import User


def get_by_email(
    db: Session,
    email: str
):
    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

def get_by_id(
    db: Session,
    user_id: int
):
    return (
    db.query(User)
    .filter(User.id == user_id)
    .first()
    )


def create_user(
    db: Session,
    email: str,
    name: str,
    picture: str,
    provider_id: str,
):
    user = User(
        email=email,
        name=name,
        picture=picture,
        provider="google",
        provider_id=provider_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user