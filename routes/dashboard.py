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
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user, require_auth
from models.category import Category
from models.item import InventoryItem
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    # Total items count
    total_items_result = await db.execute(
        select(func.count(InventoryItem.id))
    )
    total_items = total_items_result.scalar() or 0

    # Total inventory value
    total_value_result = await db.execute(
        select(func.coalesce(func.sum(InventoryItem.quantity * InventoryItem.unit_price), 0.0))
    )
    total_value = total_value_result.scalar() or 0.0

    # Low-stock count (quantity > 0 and quantity <= reorder_level)
    low_stock_count_result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.quantity > 0,
            InventoryItem.quantity <= InventoryItem.reorder_level,
        )
    )
    low_stock_count = low_stock_count_result.scalar() or 0

    # Out-of-stock count
    out_of_stock_count_result = await db.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.quantity <= 0,
        )
    )
    out_of_stock_count = out_of_stock_count_result.scalar() or 0

    # Total users count
    total_users_result = await db.execute(
        select(func.count(User.id))
    )
    total_users = total_users_result.scalar() or 0

    stats = {
        "total_items": total_items,
        "total_value": float(total_value),
        "low_stock_count": low_stock_count + out_of_stock_count,
        "total_users": total_users,
    }

    # Low-stock items (quantity <= reorder_level, including out of stock)
    low_stock_items_result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.category))
        .where(
            InventoryItem.quantity <= InventoryItem.reorder_level,
        )
        .order_by(InventoryItem.quantity.asc())
        .limit(20)
    )
    low_stock_items_raw = low_stock_items_result.scalars().all()

    low_stock_items = []
    for item in low_stock_items_raw:
        low_stock_items.append({
            "id": item.id,
            "name": item.name,
            "category_name": item.category.name if item.category else "Uncategorized",
            "quantity": item.quantity,
            "reorder_level": item.reorder_level,
        })

    # Recent activity: latest items added or updated
    recent_items_result = await db.execute(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.created_by),
            selectinload(InventoryItem.category),
        )
        .order_by(InventoryItem.updated_at.desc())
        .limit(10)
    )
    recent_items_raw = recent_items_result.scalars().all()

    recent_activity = []
    for item in recent_items_raw:
        creator_name = "Unknown"
        if item.created_by:
            creator_name = item.created_by.display_name or item.created_by.username

        if item.updated_at and item.created_at and item.updated_at > item.created_at:
            action = "updated"
        else:
            action = "created"

        timestamp_str = ""
        if item.updated_at:
            try:
                timestamp_str = item.updated_at.strftime("%b %d, %Y at %I:%M %p")
            except Exception:
                timestamp_str = str(item.updated_at)

        recent_activity.append({
            "user": creator_name,
            "action": action,
            "item_name": item.name,
            "timestamp": timestamp_str,
        })

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        context={
            "current_user": current_user,
            "user_role": current_user.role,
            "stats": stats,
            "low_stock_items": low_stock_items,
            "recent_activity": recent_activity,
        },
    )