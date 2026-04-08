import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import re

import bcrypt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import (
    clear_session_cookie,
    get_current_user,
    set_session_cookie,
)
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    current_user = await get_current_user(request, db)
    if current_user is not None:
        if current_user.is_admin:
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/items", status_code=303)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "current_user": None,
            "user_role": None,
            "flash_messages": [],
            "errors": [],
            "username": "",
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""

    errors: list[str] = []

    if not username:
        errors.append("Username is required.")
    if not password:
        errors.append("Password is required.")

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "current_user": None,
                "user_role": None,
                "flash_messages": [],
                "errors": errors,
                "username": username,
            },
        )

    user = await User.get_by_username(db, username)
    if user is None:
        logger.warning("Login attempt for non-existent user '%s'.", username)
        errors.append("Invalid username or password.")
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "current_user": None,
                "user_role": None,
                "flash_messages": [],
                "errors": errors,
                "username": username,
            },
        )

    if not bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8")):
        logger.warning("Failed login attempt for user '%s'.", username)
        errors.append("Invalid username or password.")
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "current_user": None,
                "user_role": None,
                "flash_messages": [],
                "errors": errors,
                "username": username,
            },
        )

    logger.info("User '%s' logged in successfully.", username)

    if user.is_admin:
        redirect_url = "/dashboard"
    else:
        redirect_url = "/items"

    response = RedirectResponse(url=redirect_url, status_code=303)
    set_session_cookie(response, user)
    return response


@router.get("/register")
async def register_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    current_user = await get_current_user(request, db)
    if current_user is not None:
        if current_user.is_admin:
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/items", status_code=303)

    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "current_user": None,
            "user_role": None,
            "flash_messages": [],
            "errors": [],
            "form_data": {"username": "", "display_name": ""},
        },
    )


@router.post("/register")
async def register_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    form = await request.form()
    username = (form.get("username") or "").strip()
    display_name = (form.get("display_name") or "").strip()
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password") or ""

    form_data = {
        "username": username,
        "display_name": display_name,
    }

    errors: list[str] = []

    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username) > 50:
        errors.append("Username must be at most 50 characters.")
    elif not re.match(r"^[a-zA-Z0-9_]+$", username):
        errors.append("Username may only contain letters, numbers, and underscores.")

    if not display_name:
        errors.append("Display name is required.")
    elif len(display_name) > 100:
        errors.append("Display name must be at most 100 characters.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")

    if password and password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "current_user": None,
                "user_role": None,
                "flash_messages": [],
                "errors": errors,
                "form_data": form_data,
            },
        )

    existing_user = await User.get_by_username(db, username)
    if existing_user is not None:
        errors.append("Username is already taken.")
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "current_user": None,
                "user_role": None,
                "flash_messages": [],
                "errors": errors,
                "form_data": form_data,
            },
        )

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    new_user = User(
        username=username,
        display_name=display_name,
        hashed_password=hashed_password,
        role="staff",
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    logger.info("New staff user '%s' registered successfully.", username)

    response = RedirectResponse(url="/items", status_code=303)
    set_session_cookie(response, new_user)
    return response


@router.get("/logout")
async def logout(request: Request) -> Response:
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    logger.info("User logged out.")
    return response