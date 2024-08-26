from app.api.v1.endpoints import auth, user, event, reservation, waiting_list, report
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

api_router.include_router(
    waiting_list.router,
    prefix="/waiting-list",
    tags=["Waiting List"],
)

api_router.include_router(
    report.router,
    prefix="/report",
    tags=["Report"],
)