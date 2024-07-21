from app.api.v1.endpoints import auth, user
from fastapi import APIRouter

api_router = APIRouter()


api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

api_router.include_router(
    user.router,
    prefix="/user",
    tags=["User"],
)
