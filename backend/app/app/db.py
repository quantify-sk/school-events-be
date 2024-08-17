from datetime import datetime
import sys

from app.context_manager import context_db_session
from app.data_adapter import User
from app.dependencies import SessionLocal, get_password_hash
from app.data_adapter.event import Event
from app.data_adapter.school import School


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
            role="admin",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    print("SEED ADMIN USER OK")


def seed_users():
    """Seed admin, organizer, and school representative users"""
    print("SEEDING USERS")

    db = SessionLocal()
    context_db_session.set(db)

    # Manually defined users with roles
    manual_users = [
        ("Organizer", "One", "organizer1@example.com", "organizer", None),
        ("Organizer", "Two", "organizer2@example.com", "organizer", None),
        (
            "School",
            "Rep One",
            "schoolrep1@example.com",
            "school_representative",
            {
                "name": "School One",
                "address": "123 Education St",
                "city": "Cityville",
                "ico": "12345678",
            },
        ),
        (
            "School",
            "Rep Two",
            "schoolrep2@example.com",
            "school_representative",
            {
                "name": "School Two",
                "address": "456 Learning Ave",
                "city": "Townsburg",
                "ico": "87654321",
            },
        ),
    ]
    password_hash = get_password_hash("password123")

    for first_name, last_name, email, role, school_data in manual_users:
        if role == "school_representative" and school_data:
            # Create school first
            school = School(
                name=school_data["name"],
                address=school_data["address"],
                city=school_data["city"],
                ico=school_data["ico"],
            )
            db.add(school)
            db.flush()  # This will assign an ID to the school without committing the transaction

            # Create user with school_id
            user = User(
                first_name=first_name,
                last_name=last_name,
                user_email=email,
                password_hash=password_hash,
                role=role,
                school_id=school.id,
            )
        else:
            # Create user without school_id for non-school representatives
            user = User(
                first_name=first_name,
                last_name=last_name,
                user_email=email,
                password_hash=password_hash,
                role=role,
            )

        db.add(user)

    db.commit()
    db.refresh(user)

    print("USERS AND SCHOOLS SEEDED SUCCESSFULLY")


def seed_events():
    """Seed events"""
    print("SEEDING EVENTS")

    db = SessionLocal()
    context_db_session.set(db)

    # Get organizer IDs
    organizers = db.query(User).filter(User.role == "organizer").all()
    if not organizers:
        print("No organizers found. Please seed users first.")
        return

    # Manually defined events
    events = [
        (
            "Cultural Festival",
            datetime(2024, 8, 20, 10, 0),
            datetime(2024, 8, 20, 12, 0),
            "City Hall",
            "New York",
            40.7128,
            -74.0060,
            500,
            "A celebration of diverse cultures",
            "all",
            "exhibition",
            2.0,
            "Suitable for all ages",
        ),
        (
            "Science Fair",
            datetime(2024, 9, 15, 9, 0),
            datetime(2024, 9, 15, 17, 0),
            "Science Museum",
            "Boston",
            42.3601,
            -71.0589,
            200,
            "Showcasing student science projects",
            "elementary_school",
            "exhibition",
            8.0,
            "Bring your curiosity!",
        ),
        (
            "Historical Reenactment",
            datetime(2024, 10, 1, 14, 0),
            datetime(2024, 10, 1, 16, 0),
            "Liberty Square",
            "Philadelphia",
            39.9526,
            -75.1652,
            300,
            "Step back in time and experience history",
            "high_school",
            "theater",
            2.0,
            "Educational and entertaining",
        ),
    ]

    for (
        title,
        date,
        time,
        address,
        city,
        latitude,
        longitude,
        capacity,
        description,
        target_group,
        event_type,
        duration,
        parent_info,
    ) in events:
        event = Event(
            title=title,
            date=date,
            time=time,
            address=address,
            city=city,
            latitude=latitude,
            longitude=longitude,
            capacity=capacity,
            description=description,
            target_group=target_group,
            event_type=event_type,
            duration=duration,
            parent_info=parent_info,
            status="SCHEDULED",
            organizer_id=organizers[
                events.index(
                    (
                        title,
                        date,
                        time,
                        address,
                        city,
                        latitude,
                        longitude,
                        capacity,
                        description,
                        target_group,
                        event_type,
                        duration,
                        parent_info,
                    )
                )
                % len(organizers)
            ].user_id,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

    print("EVENTS SEEDED SUCCESSFULLY")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "users":
            seed_users()
        elif sys.argv[1] == "events":
            seed_events()
        elif sys.argv[1] == "admin":
            seed_only_admin_user()
        elif sys.argv[1] == "all":
            seed_users()
            seed_events()
    else:
        print("Usage: python -m app.db seed [users|events|all]")
