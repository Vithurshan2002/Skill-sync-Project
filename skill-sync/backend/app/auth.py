import hashlib
import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import AccessToken, User, utcnow
from app.serializers import aware, identity

password_hash = PasswordHash.recommended()
_dummy_hash = password_hash.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False, description="Paste accessToken from register or login.")
Db = Annotated[Session, Depends(get_db)]


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, user: User, minutes: int) -> dict:
    token = secrets.token_urlsafe(48)
    expires = utcnow() + timedelta(minutes=minutes)
    db.add(AccessToken(digest=token_digest(token), user_id=user.id, expires_at=expires))
    db.flush()
    return {
        "accessToken": token,
        "tokenType": "bearer",
        "expiresAt": expires,
        "user": identity(db, user),
    }


def verify_password(password: str, user: User | None) -> bool:
    return (
        password_hash.verify(password, user.password_hash if user else _dummy_hash)
        and user is not None
    )


def current_user(
    request: Request,
    db: Db,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise ApiError(401, "unauthenticated", "A bearer access token is required.")
    token = db.get(AccessToken, token_digest(credentials.credentials))
    if token is None or aware(token.expires_at) <= utcnow():
        raise ApiError(401, "unauthenticated", "Your access token is invalid or expired.")
    user = db.get(User, token.user_id)
    if user is None:
        raise ApiError(401, "unauthenticated", "Your account is unavailable.")
    request.state.token_digest = token.digest
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise ApiError(403, "forbidden", "Your role cannot perform this action.")


def admin_user(user: CurrentUser) -> User:
    require_role(user, "admin")
    return user


Admin = Annotated[User, Depends(admin_user)]


def own_worker(db: Session, user: User, lock: bool = False):
    from app.models import Worker

    require_role(user, "worker")
    statement = select(Worker).where(Worker.user_id == user.id)
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)
