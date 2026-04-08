import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from typing import AsyncGenerator

import bcrypt
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base, get_db
from dependencies import create_session_cookie, COOKIE_NAME
from main import app
from models.category import Category
from models.item import InventoryItem
from models.user import User


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        username="testadmin",
        display_name="Test Admin",
        hashed_password=_hash_password("adminpass123"),
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession) -> User:
    user = User(
        username="teststaff",
        display_name="Test Staff",
        hashed_password=_hash_password("staffpass123"),
        role="staff",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_categories(db_session: AsyncSession) -> list[Category]:
    categories = [
        Category(name="Electronics", color="#3B82F6"),
        Category(name="Clothing", color="#8B5CF6"),
        Category(name="Office Supplies", color="#F59E0B"),
    ]
    for cat in categories:
        db_session.add(cat)
    await db_session.commit()
    for cat in categories:
        await db_session.refresh(cat)
    return categories


@pytest_asyncio.fixture
async def test_items(
    db_session: AsyncSession,
    test_categories: list[Category],
    admin_user: User,
) -> list[InventoryItem]:
    items = [
        InventoryItem(
            name="Wireless Mouse",
            sku="WM-001",
            description="A high-quality wireless mouse",
            quantity=50,
            unit_price=29.99,
            reorder_level=10,
            category_id=test_categories[0].id,
            created_by_id=admin_user.id,
        ),
        InventoryItem(
            name="USB Keyboard",
            sku="KB-002",
            description="Mechanical USB keyboard",
            quantity=5,
            unit_price=79.99,
            reorder_level=10,
            category_id=test_categories[0].id,
            created_by_id=admin_user.id,
        ),
        InventoryItem(
            name="T-Shirt",
            sku="TS-001",
            description="Cotton t-shirt, size M",
            quantity=0,
            unit_price=19.99,
            reorder_level=5,
            category_id=test_categories[1].id,
            created_by_id=admin_user.id,
        ),
    ]
    for item in items:
        db_session.add(item)
    await db_session.commit()
    for item in items:
        await db_session.refresh(item)
    return items


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_client(admin_user: User) -> AsyncGenerator[httpx.AsyncClient, None]:
    cookie_value = create_session_cookie(admin_user.id, admin_user.role)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        cookies={COOKIE_NAME: cookie_value},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def staff_client(staff_user: User) -> AsyncGenerator[httpx.AsyncClient, None]:
    cookie_value = create_session_cookie(staff_user.id, staff_user.role)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        cookies={COOKIE_NAME: cookie_value},
    ) as ac:
        yield ac