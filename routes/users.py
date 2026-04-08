import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import require_admin
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users")
async def list_users(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    from main import templates

    users = await User.get_all(db)

    flash_messages = []
    flash = request.cookies.get("flash_message")
    flash_cat = request.cookies.get("flash_category", "info")
    if flash:
        flash_messages.append({"text": flash, "category": flash_cat})

    response = templates.TemplateResponse(
        request,
        "users/list.html",
        context={
            "users": users,
            "current_user": current_user,
            "user_role": current_user.role,
            "admin_username": settings.ADMIN_USERNAME,
            "flash_messages": flash_messages,
        },
    )

    if flash:
        response.delete_cookie("flash_message", path="/")
        response.delete_cookie("flash_category", path="/")

    return response


@router.post("/users")
async def create_user(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    username = username.strip()
    display_name = display_name.strip()

    errors: list[str] = []

    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    if len(username) > 50:
        errors.append("Username must be at most 50 characters.")
    if not display_name:
        errors.append("Display name is required.")
    if len(display_name) > 100:
        errors.append("Display name must be at most 100 characters.")
    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if role not in ("admin", "staff"):
        errors.append("Role must be either 'admin' or 'staff'.")

    if not errors:
        existing = await User.get_by_username(db, username)
        if existing:
            errors.append(f"Username '{username}' is already taken.")

    if errors:
        from main import templates

        users = await User.get_all(db)
        flash_messages = [{"text": e, "category": "error"} for e in errors]

        return templates.TemplateResponse(
            request,
            "users/list.html",
            context={
                "users": users,
                "current_user": current_user,
                "user_role": current_user.role,
                "admin_username": settings.ADMIN_USERNAME,
                "flash_messages": flash_messages,
            },
            status_code=200,
        )

    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    new_user = User(
        username=username,
        display_name=display_name,
        hashed_password=hashed,
        role=role,
    )
    db.add(new_user)
    await db.flush()

    logger.info(
        "Admin '%s' created new user '%s' with role '%s'.",
        current_user.username,
        username,
        role,
    )

    response = RedirectResponse(url="/users", status_code=303)
    response.set_cookie(
        key="flash_message",
        value=f"User '{username}' created successfully.",
        max_age=10,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="flash_category",
        value="success",
        max_age=10,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/users/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    target_user = await User.get_by_id(db, user_id)

    if target_user is None:
        logger.warning(
            "Admin '%s' attempted to delete non-existent user_id=%s.",
            current_user.username,
            user_id,
        )
        response = RedirectResponse(url="/users", status_code=303)
        response.set_cookie(
            key="flash_message",
            value="User not found.",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            key="flash_category",
            value="error",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response

    if target_user.id == current_user.id:
        logger.warning(
            "Admin '%s' attempted to delete their own account.",
            current_user.username,
        )
        response = RedirectResponse(url="/users", status_code=303)
        response.set_cookie(
            key="flash_message",
            value="You cannot delete your own account.",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            key="flash_category",
            value="error",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response

    if target_user.username == settings.ADMIN_USERNAME:
        logger.warning(
            "Admin '%s' attempted to delete the default admin account '%s'.",
            current_user.username,
            settings.ADMIN_USERNAME,
        )
        response = RedirectResponse(url="/users", status_code=303)
        response.set_cookie(
            key="flash_message",
            value="Cannot delete the default admin account.",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            key="flash_category",
            value="error",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response

    deleted_username = target_user.username
    await db.delete(target_user)
    await db.flush()

    logger.info(
        "Admin '%s' deleted user '%s' (id=%s).",
        current_user.username,
        deleted_username,
        user_id,
    )

    response = RedirectResponse(url="/users", status_code=303)
    response.set_cookie(
        key="flash_message",
        value=f"User '{deleted_username}' has been deleted.",
        max_age=10,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="flash_category",
        value="success",
        max_age=10,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response