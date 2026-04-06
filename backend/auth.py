"""
auth.py — JWT HS256 usando apenas stdlib (hmac + hashlib + base64 + json).
Sem dependências externas.
"""
import base64
import hmac
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User

SECRET_KEY        = os.getenv("JWT_SECRET", "aromap-dev-secret-key-2025-change-in-production").encode()
TOKEN_EXPIRE_DAYS = 7

bearer_scheme = HTTPBearer()


# ── Helpers base64url ─────────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (padding % 4))


# ── Criar token ───────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    exp     = int((datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)).timestamp())
    payload = _b64url_encode(json.dumps({"sub": user_id, "exp": exp}).encode())

    signing_input = f"{header}.{payload}".encode()
    sig = _b64url_encode(hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest())

    return f"{header}.{payload}.{sig}"


# ── Validar token ─────────────────────────────────────────────────────────────

def _decode_token(token: str) -> Optional[dict]:
    try:
        header, payload, sig = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header}.{payload}".encode()
    expected_sig  = _b64url_encode(hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest())

    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        data = json.loads(_b64url_decode(payload))
    except Exception:
        return None

    exp = data.get("exp", 0)
    if datetime.now(timezone.utc).timestamp() > exp:
        return None

    return data


# ── Dependência FastAPI ───────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = _decode_token(credentials.credentials)
    if not payload:
        raise exc

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise exc

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise exc

    return user
