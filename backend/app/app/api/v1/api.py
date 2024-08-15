from app.api.v1.endpoints import auth, user, event, reservation
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

api_router.include_router(
    event.router,
    prefix="/event",
    tags=["Event"],
)

api_router.include_router(
    reservation.router,
    prefix="/reservation",
    tags=["Reservation"],
)
