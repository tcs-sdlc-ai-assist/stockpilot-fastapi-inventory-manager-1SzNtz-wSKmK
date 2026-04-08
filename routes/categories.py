import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_auth
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/categories")
async def list_categories(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(Category).order_by(Category.name.asc())
    )
    categories = list(result.scalars().all())

    categories_with_counts = []
    for category in categories:
        count_result = await db.execute(
            select(func.count(InventoryItem.id)).where(
                InventoryItem.category_id == category.id
            )
        )
        item_count = count_result.scalar() or 0

        categories_with_counts.append(
            {
                "id": category.id,
                "name": category.name,
                "color": category.color,
                "item_count": item_count,
            }
        )

    flash_messages = request.session.pop("flash_messages", []) if hasattr(request, "session") else []

    return templates.TemplateResponse(
        request,
        "categories/list.html",
        context={
            "categories": categories_with_counts,
            "current_user": current_user,
            "user_role": current_user.role,
            "flash_messages": flash_messages,
        },
    )


@router.post("/categories")
async def create_category(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    form = await request.form()
    name = form.get("name", "").strip()
    color = form.get("color", "#0d9488").strip()

    errors: list[str] = []

    if not name:
        errors.append("Category name is required.")
    elif len(name) > 50:
        errors.append("Category name must be 50 characters or fewer.")

    if not color or len(color) != 7 or not color.startswith("#"):
        errors.append("A valid hex color is required (e.g. #0d9488).")

    if not errors:
        existing_result = await db.execute(
            select(Category).where(func.lower(Category.name) == name.lower())
        )
        existing = existing_result.scalars().first()
        if existing:
            errors.append(f"A category named '{name}' already exists.")

    if errors:
        result = await db.execute(
            select(Category).order_by(Category.name.asc())
        )
        categories = list(result.scalars().all())

        categories_with_counts = []
        for category in categories:
            count_result = await db.execute(
                select(func.count(InventoryItem.id)).where(
                    InventoryItem.category_id == category.id
                )
            )
            item_count = count_result.scalar() or 0
            categories_with_counts.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "color": category.color,
                    "item_count": item_count,
                }
            )

        flash_messages = [{"category": "error", "text": e} for e in errors]

        return templates.TemplateResponse(
            request,
            "categories/list.html",
            context={
                "categories": categories_with_counts,
                "current_user": current_user,
                "user_role": current_user.role,
                "flash_messages": flash_messages,
            },
            status_code=422,
        )

    new_category = Category(name=name, color=color)
    db.add(new_category)
    await db.flush()

    logger.info(
        "Category '%s' created by user '%s' (id=%s).",
        name,
        current_user.username,
        current_user.id,
    )

    response = RedirectResponse(url="/categories", status_code=303)
    return response


@router.post("/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalars().first()

    if category is None:
        logger.warning(
            "User '%s' attempted to delete non-existent category id=%s.",
            current_user.username,
            category_id,
        )
        response = RedirectResponse(url="/categories", status_code=303)
        return response

    count_result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.category_id == category_id
        )
    )
    item_count = count_result.scalar() or 0

    if item_count > 0:
        logger.warning(
            "User '%s' attempted to delete category '%s' (id=%s) which has %d item(s).",
            current_user.username,
            category.name,
            category_id,
            item_count,
        )

        all_categories_result = await db.execute(
            select(Category).order_by(Category.name.asc())
        )
        categories = list(all_categories_result.scalars().all())

        categories_with_counts = []
        for cat in categories:
            cat_count_result = await db.execute(
                select(func.count(InventoryItem.id)).where(
                    InventoryItem.category_id == cat.id
                )
            )
            cat_item_count = cat_count_result.scalar() or 0
            categories_with_counts.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "color": cat.color,
                    "item_count": cat_item_count,
                }
            )

        flash_messages = [
            {
                "category": "error",
                "text": f"Cannot delete category '{category.name}' — it has {item_count} item{'s' if item_count != 1 else ''} assigned to it.",
            }
        ]

        return templates.TemplateResponse(
            request,
            "categories/list.html",
            context={
                "categories": categories_with_counts,
                "current_user": current_user,
                "user_role": current_user.role,
                "flash_messages": flash_messages,
            },
            status_code=409,
        )

    category_name = category.name
    await db.delete(category)
    await db.flush()

    logger.info(
        "Category '%s' (id=%s) deleted by user '%s' (id=%s).",
        category_name,
        category_id,
        current_user.username,
        current_user.id,
    )

    response = RedirectResponse(url="/categories", status_code=303)
    return response