import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging

from sqlalchemy import select

from config import settings
from database import async_session_maker, init_db
from models.category import Category
from models.user import User

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    {"name": "Electronics", "color": "#3B82F6"},
    {"name": "Clothing", "color": "#8B5CF6"},
    {"name": "Food & Beverage", "color": "#EF4444"},
    {"name": "Office Supplies", "color": "#F59E0B"},
    {"name": "Tools", "color": "#6B7280"},
    {"name": "Other", "color": "#0D9488"},
]


async def _seed_admin(session) -> None:
    existing = await User.get_by_username(session, settings.ADMIN_USERNAME)
    if existing:
        logger.info("Admin user '%s' already exists — skipping.", settings.ADMIN_USERNAME)
        return

    import bcrypt

    hashed = bcrypt.hashpw(
        settings.ADMIN_PASSWORD.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    admin = User(
        username=settings.ADMIN_USERNAME,
        display_name=settings.ADMIN_DISPLAY_NAME,
        hashed_password=hashed,
        role="admin",
    )
    session.add(admin)
    await session.flush()
    logger.info("Default admin user '%s' created successfully.", settings.ADMIN_USERNAME)


async def _seed_categories(session) -> None:
    for cat_data in DEFAULT_CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalars().first()
        if existing:
            logger.debug("Category '%s' already exists — skipping.", cat_data["name"])
            continue

        category = Category(name=cat_data["name"], color=cat_data["color"])
        session.add(category)
        await session.flush()
        logger.info("Category '%s' created with color %s.", cat_data["name"], cat_data["color"])


async def run_seeding() -> None:
    logger.info("Starting database seeding...")

    await init_db()

    async with async_session_maker() as session:
        try:
            await _seed_admin(session)
            await _seed_categories(session)
            await session.commit()
            logger.info("Database seeding completed successfully.")
        except Exception:
            await session.rollback()
            logger.exception("Database seeding failed.")
            raise