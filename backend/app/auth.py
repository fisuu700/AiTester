"""Authentification : hash bcrypt + JWT + dépendances FastAPI."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Session expirée, reconnectez-vous.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Token invalide.") from exc


def user_from_token(token: str | None, db: Session) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    return user_from_token(token, db)


def get_user_from_query_token(token: str | None = Query(default=None), db: Session = Depends(get_db)) -> User:
    """Variante pour les WebSockets (le header Authorization n'est pas disponible)."""
    return user_from_token(token, db)


def get_user_from_api_key(x_api_key: str | None = None, db: Session = Depends(get_db)) -> User | None:
    if not x_api_key:
        return None
    return db.scalar(select(User).where(User.api_key == x_api_key))


def generate_api_key() -> str:
    return "ait_" + secrets.token_urlsafe(32)


def get_actor(request: Request, db: Session = Depends(get_db)) -> User:
    """Authentification souple : X-API-Key (CI/CD) ou Bearer JWT."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        user = db.scalar(select(User).where(User.api_key == api_key))
        if user is None:
            raise HTTPException(status_code=401, detail="Clé API invalide.")
        return user

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return user_from_token(authorization.split(" ", 1)[1], db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise (Bearer JWT ou X-API-Key).",
        headers={"WWW-Authenticate": "Bearer"},
    )
