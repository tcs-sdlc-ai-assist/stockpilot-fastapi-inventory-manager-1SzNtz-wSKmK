import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User

logger = logging.getLogger(__name__)

COOKIE_NAME = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY)


def create_session_cookie(user_id: int, role: str) -> str:
    serializer = _get_serializer()
    return serializer.dumps({"user_id": user_id, "role": role})


def decode_session_cookie(cookie_value: str) -> Optional[dict]:
    serializer = _get_serializer()
    try:
        data = serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
        return data
    except SignatureExpired:
        logger.warning("Session cookie expired.")
        return None
    except BadSignature:
        logger.warning("Invalid session cookie signature.")
        return None
    except Exception:
        logger.exception("Unexpected error decoding session cookie.")
        return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    cookie_value = request.cookies.get(COOKIE_NAME)
    if not cookie_value:
        return None

    session_data = decode_session_cookie(cookie_value)
    if not session_data:
        return None

    user_id = session_data.get("user_id")
    if user_id is None:
        return None

    user = await User.get_by_id(db, int(user_id))
    if user is None:
        logger.warning("Session references non-existent user_id=%s.", user_id)
        return None

    return user


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await get_current_user(request, db)
    if user is None:
        raise _redirect_to_login()
    return user


async def require_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await require_auth(request, db)
    if not user.is_admin:
        logger.warning(
            "Non-admin user '%s' attempted to access admin-only resource.",
            user.username,
        )
        raise _redirect_to_dashboard()
    return user


def _redirect_to_login() -> Exception:
    from fastapi import HTTPException

    response = RedirectResponse(url="/login", status_code=303)
    raise HTTPException(status_code=303, detail="Authentication required")


def _redirect_to_dashboard() -> Exception:
    from fastapi import HTTPException

    response = RedirectResponse(url="/dashboard", status_code=303)
    raise HTTPException(status_code=303, detail="Admin access required")


def set_session_cookie(response: RedirectResponse, user: User) -> None:
    cookie_value = create_session_cookie(user.id, user.role)
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie_value,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_session_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )