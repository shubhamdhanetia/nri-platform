from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine

from app.api.auth import router as auth_router
from app.api.locations import router as locations_router
from app.api.rides import router as rides_router
from app.api.users import router as users_router
from app.api.posts import (
    router as posts_router
)

import app.models.user
import app.models.post
import app.models.comment
import app.models.reaction
import app.models.saved_post
import app.models.ride
from app.models.ride import ride_browse_index, ride_pickup_h3_index

Base.metadata.create_all(bind=engine)
ride_pickup_h3_index.create(bind=engine, checkfirst=True)
ride_browse_index.create(bind=engine, checkfirst=True)

app = FastAPI(title="NRI Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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