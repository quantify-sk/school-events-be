import sys

from app.context_manager import context_db_session
from app.data_adapter import User
from app.dependencies import SessionLocal, get_password_hash


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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "admin":
        seed_only_admin_user()
    else:
        print("Usage: python -m app.db seed")
