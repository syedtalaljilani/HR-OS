from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services import audit_service as audit
from app.utils.common import jsonify_data, jsonify_uuid


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    return user


def login(db: Session, data: LoginRequest) -> tuple[User, str]:
    user = authenticate(db, data.email, data.password)
    token = create_access_token(user.id)
    return user, token


def create_user(db: Session, data: UserCreate) -> User:
    email = data.email.lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        name=data.name,
        email=email,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    audit.log_action(
        db,
        user_id=None,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        new_value=jsonify_data(user),
    )
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data) -> User:
    updates = data.model_dump(exclude_unset=True)
    password = updates.pop("password", None)
    if "email" in updates:
        updates["email"] = updates["email"].lower()
    if password:
        updates["password_hash"] = get_password_hash(password)
    old_value = jsonify_data(user)
    for key, value in updates.items():
        setattr(user, key, value)
    db.flush()
    audit.log_action(
        db,
        user_id=None,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        old_value=old_value,
        new_value=jsonify_data(user),
    )
    db.commit()
    db.refresh(user)
    return user