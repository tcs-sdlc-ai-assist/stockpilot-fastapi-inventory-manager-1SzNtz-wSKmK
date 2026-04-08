import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user, require_auth
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ITEMS_PER_PAGE = 12


def _flash(request: Request, message: str, category: str = "info") -> None:
    if "_flash_messages" not in request.state.__dict__:
        request.state._flash_messages = []
    request.state._flash_messages.append({"text": message, "category": category})


def _get_flash_messages(request: Request) -> list[dict]:
    messages = getattr(request.state, "_flash_messages", [])
    return messages


def _base_context(request: Request, user: Optional[User]) -> dict:
    return {
        "current_user": user,
        "user_role": user.role if user else None,
        "flash_messages": _get_flash_messages(request),
    }


@router.get("/items")
async def list_items(
    request: Request,
    search: str = Query("", alias="search"),
    category_id: str = Query("", alias="category"),
    sort: str = Query("name_asc", alias="sort"),
    page: int = Query(1, ge=1, alias="page"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    stmt = select(InventoryItem).options(
        selectinload(InventoryItem.category),
        selectinload(InventoryItem.created_by),
    )

    if search.strip():
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                InventoryItem.name.ilike(search_term),
                InventoryItem.sku.ilike(search_term),
            )
        )

    if category_id.strip():
        try:
            cat_id_int = int(category_id.strip())
            stmt = stmt.where(InventoryItem.category_id == cat_id_int)
        except ValueError:
            pass

    sort_mapping = {
        "name_asc": InventoryItem.name.asc(),
        "name_desc": InventoryItem.name.desc(),
        "quantity_asc": InventoryItem.quantity.asc(),
        "quantity_desc": InventoryItem.quantity.desc(),
        "price_asc": InventoryItem.unit_price.asc(),
        "price_desc": InventoryItem.unit_price.desc(),
        "date_desc": InventoryItem.created_at.desc(),
        "date_asc": InventoryItem.created_at.asc(),
    }
    order_clause = sort_mapping.get(sort, InventoryItem.name.asc())
    stmt = stmt.order_by(order_clause)

    count_stmt = select(func.count()).select_from(InventoryItem)
    if search.strip():
        search_term = f"%{search.strip()}%"
        count_stmt = count_stmt.where(
            or_(
                InventoryItem.name.ilike(search_term),
                InventoryItem.sku.ilike(search_term),
            )
        )
    if category_id.strip():
        try:
            cat_id_int = int(category_id.strip())
            count_stmt = count_stmt.where(InventoryItem.category_id == cat_id_int)
        except ValueError:
            pass

    total_result = await db.execute(count_stmt)
    total_items = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * ITEMS_PER_PAGE
    stmt = stmt.offset(offset).limit(ITEMS_PER_PAGE)

    result = await db.execute(stmt)
    items = list(result.scalars().all())

    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = list(cat_result.scalars().all())

    context = _base_context(request, current_user)
    context.update(
        {
            "inventory_items": items,
            "categories": categories,
            "search": search,
            "selected_category": category_id,
            "sort": sort,
            "page": page,
            "total_pages": total_pages,
        }
    )

    return templates.TemplateResponse(request, "inventory/list.html", context=context)


@router.get("/items/new")
async def add_item_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Response:
    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = list(cat_result.scalars().all())

    context = _base_context(request, current_user)
    context.update(
        {
            "item": None,
            "categories": categories,
            "form_data": None,
            "errors": None,
        }
    )

    return templates.TemplateResponse(request, "inventory/form.html", context=context)


@router.post("/items/add")
async def add_item_submit(
    request: Request,
    name: str = Form(""),
    sku: str = Form(""),
    description: str = Form(""),
    category_id: str = Form(""),
    quantity: str = Form(""),
    unit_price: str = Form(""),
    reorder_level: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Response:
    form_data = {
        "name": name.strip(),
        "sku": sku.strip(),
        "description": description.strip(),
        "category_id": category_id.strip(),
        "quantity": quantity.strip(),
        "unit_price": unit_price.strip(),
        "reorder_level": reorder_level.strip(),
    }

    errors = _validate_item_form(form_data)

    if not errors:
        existing_sku = None
        if form_data["sku"]:
            sku_result = await db.execute(
                select(InventoryItem).where(InventoryItem.sku == form_data["sku"])
            )
            existing_sku = sku_result.scalars().first()
        if existing_sku:
            errors["sku"] = "An item with this SKU already exists."

    if errors:
        cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
        categories = list(cat_result.scalars().all())

        context = _base_context(request, current_user)
        context.update(
            {
                "item": None,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
            }
        )
        return templates.TemplateResponse(
            request, "inventory/form.html", context=context, status_code=422
        )

    item = InventoryItem(
        name=form_data["name"],
        sku=form_data["sku"] if form_data["sku"] else None,
        description=form_data["description"] if form_data["description"] else None,
        quantity=int(form_data["quantity"]),
        unit_price=float(form_data["unit_price"]),
        reorder_level=int(form_data["reorder_level"]) if form_data["reorder_level"] else 10,
        category_id=int(form_data["category_id"]),
        created_by_id=current_user.id,
    )
    db.add(item)
    await db.flush()

    logger.info(
        "User '%s' created inventory item '%s' (id=%s).",
        current_user.username,
        item.name,
        item.id,
    )

    _flash(request, f"Item \"{item.name}\" created successfully.", "success")

    response = RedirectResponse(url="/items", status_code=303)
    return response


@router.get("/items/{item_id}")
async def item_detail(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.created_by),
        )
        .where(InventoryItem.id == item_id)
    )
    item = result.scalars().first()

    if item is None:
        context = _base_context(request, current_user)
        return templates.TemplateResponse(
            request, "errors/404.html", context=context, status_code=404
        )

    can_edit = False
    can_delete = False
    if current_user:
        if current_user.is_admin:
            can_edit = True
            can_delete = True
        elif item.created_by_id == current_user.id:
            can_edit = True
            can_delete = True

    context = _base_context(request, current_user)
    context.update(
        {
            "item": item,
            "created_by_user": item.created_by,
            "can_edit": can_edit,
            "can_delete": can_delete,
        }
    )

    return templates.TemplateResponse(request, "inventory/detail.html", context=context)


@router.get("/items/{item_id}/edit")
async def edit_item_form(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Response:
    result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.created_by),
        )
        .where(InventoryItem.id == item_id)
    )
    item = result.scalars().first()

    if item is None:
        context = _base_context(request, current_user)
        return templates.TemplateResponse(
            request, "errors/404.html", context=context, status_code=404
        )

    if not current_user.is_admin and item.created_by_id != current_user.id:
        logger.warning(
            "User '%s' attempted to edit item '%s' owned by user_id=%s.",
            current_user.username,
            item.name,
            item.created_by_id,
        )
        _flash(request, "You do not have permission to edit this item.", "error")
        return RedirectResponse(url=f"/items/{item_id}", status_code=303)

    cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
    categories = list(cat_result.scalars().all())

    context = _base_context(request, current_user)
    context.update(
        {
            "item": item,
            "categories": categories,
            "form_data": None,
            "errors": None,
        }
    )

    return templates.TemplateResponse(request, "inventory/form.html", context=context)


@router.post("/items/{item_id}/edit")
async def edit_item_submit(
    request: Request,
    item_id: int,
    name: str = Form(""),
    sku: str = Form(""),
    description: str = Form(""),
    category_id: str = Form(""),
    quantity: str = Form(""),
    unit_price: str = Form(""),
    reorder_level: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Response:
    result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.created_by),
        )
        .where(InventoryItem.id == item_id)
    )
    item = result.scalars().first()

    if item is None:
        context = _base_context(request, current_user)
        return templates.TemplateResponse(
            request, "errors/404.html", context=context, status_code=404
        )

    if not current_user.is_admin and item.created_by_id != current_user.id:
        logger.warning(
            "User '%s' attempted to edit item '%s' owned by user_id=%s.",
            current_user.username,
            item.name,
            item.created_by_id,
        )
        _flash(request, "You do not have permission to edit this item.", "error")
        return RedirectResponse(url=f"/items/{item_id}", status_code=303)

    form_data = {
        "name": name.strip(),
        "sku": sku.strip(),
        "description": description.strip(),
        "category_id": category_id.strip(),
        "quantity": quantity.strip(),
        "unit_price": unit_price.strip(),
        "reorder_level": reorder_level.strip(),
    }

    errors = _validate_item_form(form_data)

    if not errors and form_data["sku"]:
        sku_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.sku == form_data["sku"],
                InventoryItem.id != item_id,
            )
        )
        existing_sku = sku_result.scalars().first()
        if existing_sku:
            errors["sku"] = "An item with this SKU already exists."

    if errors:
        cat_result = await db.execute(select(Category).order_by(Category.name.asc()))
        categories = list(cat_result.scalars().all())

        context = _base_context(request, current_user)
        context.update(
            {
                "item": item,
                "categories": categories,
                "form_data": form_data,
                "errors": errors,
            }
        )
        return templates.TemplateResponse(
            request, "inventory/form.html", context=context, status_code=422
        )

    item.name = form_data["name"]
    item.sku = form_data["sku"] if form_data["sku"] else None
    item.description = form_data["description"] if form_data["description"] else None
    item.quantity = int(form_data["quantity"])
    item.unit_price = float(form_data["unit_price"])
    item.reorder_level = int(form_data["reorder_level"]) if form_data["reorder_level"] else 10
    item.category_id = int(form_data["category_id"])

    await db.flush()

    logger.info(
        "User '%s' updated inventory item '%s' (id=%s).",
        current_user.username,
        item.name,
        item.id,
    )

    _flash(request, f"Item \"{item.name}\" updated successfully.", "success")

    return RedirectResponse(url=f"/items/{item_id}", status_code=303)


@router.post("/items/{item_id}/delete")
async def delete_item(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Response:
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    item = result.scalars().first()

    if item is None:
        context = _base_context(request, current_user)
        return templates.TemplateResponse(
            request, "errors/404.html", context=context, status_code=404
        )

    if not current_user.is_admin and item.created_by_id != current_user.id:
        logger.warning(
            "User '%s' attempted to delete item '%s' owned by user_id=%s.",
            current_user.username,
            item.name,
            item.created_by_id,
        )
        _flash(request, "You do not have permission to delete this item.", "error")
        return RedirectResponse(url=f"/items/{item_id}", status_code=303)

    item_name = item.name
    await db.delete(item)
    await db.flush()

    logger.info(
        "User '%s' deleted inventory item '%s' (id=%s).",
        current_user.username,
        item_name,
        item_id,
    )

    _flash(request, f"Item \"{item_name}\" deleted successfully.", "success")

    return RedirectResponse(url="/items", status_code=303)


def _validate_item_form(form_data: dict) -> dict:
    errors: dict[str, str] = {}

    if not form_data.get("name"):
        errors["name"] = "Item name is required."
    elif len(form_data["name"]) > 200:
        errors["name"] = "Item name must be 200 characters or fewer."

    if form_data.get("sku") and len(form_data["sku"]) > 50:
        errors["sku"] = "SKU must be 50 characters or fewer."

    if not form_data.get("category_id"):
        errors["category_id"] = "Category is required."
    else:
        try:
            int(form_data["category_id"])
        except ValueError:
            errors["category_id"] = "Invalid category selected."

    if not form_data.get("quantity"):
        errors["quantity"] = "Quantity is required."
    else:
        try:
            qty = int(form_data["quantity"])
            if qty < 0:
                errors["quantity"] = "Quantity must be 0 or greater."
        except ValueError:
            errors["quantity"] = "Quantity must be a whole number."

    if not form_data.get("unit_price"):
        errors["unit_price"] = "Unit price is required."
    else:
        try:
            price = float(form_data["unit_price"])
            if price < 0:
                errors["unit_price"] = "Unit price must be 0 or greater."
        except ValueError:
            errors["unit_price"] = "Unit price must be a valid number."

    if form_data.get("reorder_level"):
        try:
            rl = int(form_data["reorder_level"])
            if rl < 0:
                errors["reorder_level"] = "Reorder level must be 0 or greater."
        except ValueError:
            errors["reorder_level"] = "Reorder level must be a whole number."

    return errors