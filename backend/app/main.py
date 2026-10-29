from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.auth import router as auth_router
from app.api.locations import router as locations_router
from app.api.rides import router as rides_router
from app.api.carpools import router as carpools_router
from app.api.notifications import router as notifications_router
from app.api.users import router as users_router
from app.api.posts import (
    router as posts_router
)

app = FastAPI(title="NRI Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"]
)

app.include_router(
    users_router,
    prefix="/users",
    tags=["Users"]
)

app.include_router(
    posts_router,
    prefix="/posts",
    tags=["Posts"]
)

app.include_router(
    locations_router,
    prefix="/locations",
    tags=["Locations"]
)

app.include_router(rides_router, prefix="/rides", tags=["Rides"])
app.include_router(carpools_router, prefix="/rides/carpools", tags=["Carpools"])
app.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])