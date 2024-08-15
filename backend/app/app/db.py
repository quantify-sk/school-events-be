from datetime import datetime
import sys

from app.context_manager import context_db_session
from app.data_adapter import User
from app.dependencies import SessionLocal, get_password_hash
from app.data_adapter.event import Event


def seed_only_admin_user():
    """Seed only admin user"""
    print("SEED ADMIN USER")

    db = SessionLocal()

    context_db_session.set(db)

    # Manually defined users
    manual_users = [
        ("root", "root", "admin@admin.com"),
        ("root", "root", "test@test.com"),
        ("root", "root", "test1@test1.com"),
    ]
    password_hash = get_password_hash("root")

    for first_name, last_name, email in manual_users:
        user = User(
            first_name=first_name,
            last_name=last_name,
            user_email=email,
            password_hash=password_hash,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    print("SEED ADMIN USER OK")


def seed_events():
    """Seed events"""
    print("SEED EVENTS")

    db = SessionLocal()

    context_db_session.set(db)

    # Manually defined events
    events = [
        (
            "Event 1",
            datetime(2024, 8, 20, 10, 0),
            datetime(2024, 8, 20, 12, 0),
            "Location 1",
            100,
            "Description 1",
            "Group 1",
        ),
        (
            "Event 2",
            datetime(2024, 8, 21, 14, 0),
            datetime(2024, 8, 21, 16, 0),
            "Location 2",
            150,
            "Description 2",
            "Group 2",
        ),
        (
            "Event 3",
            datetime(2024, 8, 22, 9, 0),
            datetime(2024, 8, 22, 11, 0),
            "Location 3",
            200,
            "Description 3",
            "Group 3",
        ),
    ]

    for title, date, time, location, capacity, description, target_group in events:
        event = Event(
            title=title,
            date=date,
            time=time,
            location=location,
            capacity=capacity,
            description=description,
            target_group=target_group,
            status="SCHEDULED",  # Assuming default status
        )
        db.add(event)
        db.commit()
        db.refresh(event)

    print("SEED EVENTS OK")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "admin":
            seed_only_admin_user()
        elif sys.argv[1] == "events":
            seed_events()
    else:
        print("Usage: python -m app.db seed [admin|events]")
