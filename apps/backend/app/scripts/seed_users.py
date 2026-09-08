"""Seed default admin and HR users.

Run:  python -m app.scripts.seed_users
"""

from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.db.models.enums import UserRole
from app.db.models.user import User

SEED_USERS = [
    {"name": "System Admin", "email": "admin@hros.com", "password": "admin12345", "role": UserRole.ADMIN},
    {"name": "HR Manager", "email": "hr@hros.com", "password": "hr12345", "role": UserRole.HR},
]


def seed() -> int:
    db = SessionLocal()
    created = 0
    try:
        for item in SEED_USERS:
            existing = db.query(User).filter(User.email == item["email"]).first()
            if existing:
                continue
            db.add(
                User(
                    name=item["name"],
                    email=item["email"],
                    password_hash=get_password_hash(item["password"]),
                    role=item["role"],
                    is_active=True,
                )
            )
            created += 1
        db.commit()
    finally:
        db.close()
    return created


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} user(s).")