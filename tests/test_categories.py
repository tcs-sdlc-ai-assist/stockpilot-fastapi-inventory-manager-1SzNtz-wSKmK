import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx

from models.category import Category
from models.item import InventoryItem
from models.user import User


@pytest.mark.asyncio
async def test_list_categories_as_admin(
    admin_client: httpx.AsyncClient,
    test_categories: list[Category],
):
    response = await admin_client.get("/categories")
    assert response.status_code == 200
    text = response.text
    for cat in test_categories:
        assert cat.name in text


@pytest.mark.asyncio
async def test_list_categories_as_staff(
    staff_client: httpx.AsyncClient,
    test_categories: list[Category],
):
    response = await staff_client.get("/categories")
    assert response.status_code == 200
    text = response.text
    for cat in test_categories:
        assert cat.name in text


@pytest.mark.asyncio
async def test_list_categories_unauthenticated_redirects(
    client: httpx.AsyncClient,
):
    response = await client.get("/categories", follow_redirects=False)
    assert response.status_code == 303 or response.status_code == 302 or response.status_code == 200
    if response.status_code in (302, 303):
        location = response.headers.get("location", "")
        assert "login" in location.lower()


@pytest.mark.asyncio
async def test_add_category_as_admin(
    admin_client: httpx.AsyncClient,
):
    response = await admin_client.post(
        "/categories",
        data={"name": "New Test Category", "color": "#FF5733"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/categories" in location

    list_response = await admin_client.get("/categories")
    assert list_response.status_code == 200
    assert "New Test Category" in list_response.text


@pytest.mark.asyncio
async def test_add_category_as_staff(
    staff_client: httpx.AsyncClient,
):
    response = await staff_client.post(
        "/categories",
        data={"name": "Staff Category", "color": "#123456"},
        follow_redirects=False,
    )
    assert response.status_code == 303 or response.status_code == 200


@pytest.mark.asyncio
async def test_add_category_duplicate_name_rejected(
    admin_client: httpx.AsyncClient,
    test_categories: list[Category],
):
    existing_name = test_categories[0].name

    response = await admin_client.post(
        "/categories",
        data={"name": existing_name, "color": "#AABBCC"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "already exists" in response.text


@pytest.mark.asyncio
async def test_add_category_empty_name_rejected(
    admin_client: httpx.AsyncClient,
):
    response = await admin_client.post(
        "/categories",
        data={"name": "", "color": "#AABBCC"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "required" in response.text.lower()


@pytest.mark.asyncio
async def test_add_category_invalid_color_rejected(
    admin_client: httpx.AsyncClient,
):
    response = await admin_client.post(
        "/categories",
        data={"name": "Valid Name", "color": "notacolor"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "color" in response.text.lower()


@pytest.mark.asyncio
async def test_delete_empty_category_as_admin(
    admin_client: httpx.AsyncClient,
    test_categories: list[Category],
    db_session,
):
    from sqlalchemy import select, func

    cat_to_delete = test_categories[2]

    count_result = await db_session.execute(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.category_id == cat_to_delete.id
        )
    )
    item_count = count_result.scalar() or 0
    assert item_count == 0, f"Category '{cat_to_delete.name}' should have no items for this test"

    response = await admin_client.post(
        f"/categories/{cat_to_delete.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/categories" in location

    list_response = await admin_client.get("/categories")
    assert cat_to_delete.name not in list_response.text


@pytest.mark.asyncio
async def test_delete_category_with_items_blocked(
    admin_client: httpx.AsyncClient,
    test_categories: list[Category],
    test_items: list[InventoryItem],
):
    cat_with_items = test_categories[0]

    response = await admin_client.post(
        f"/categories/{cat_with_items.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 409
    assert "Cannot delete" in response.text or "cannot delete" in response.text.lower()
    assert cat_with_items.name in response.text


@pytest.mark.asyncio
async def test_delete_nonexistent_category(
    admin_client: httpx.AsyncClient,
):
    response = await admin_client.post(
        "/categories/99999/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers.get("location", "")
    assert "/categories" in location


@pytest.mark.asyncio
async def test_unauthenticated_post_category_redirects(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/categories",
        data={"name": "Unauthorized Category", "color": "#000000"},
        follow_redirects=False,
    )
    assert response.status_code == 303 or response.status_code == 302
    if response.status_code in (302, 303):
        location = response.headers.get("location", "")
        assert "login" in location.lower()


@pytest.mark.asyncio
async def test_unauthenticated_delete_category_redirects(
    client: httpx.AsyncClient,
    test_categories: list[Category],
):
    response = await client.post(
        f"/categories/{test_categories[0].id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303 or response.status_code == 302
    if response.status_code in (302, 303):
        location = response.headers.get("location", "")
        assert "login" in location.lower()


@pytest.mark.asyncio
async def test_add_category_name_too_long_rejected(
    admin_client: httpx.AsyncClient,
):
    long_name = "A" * 51
    response = await admin_client.post(
        "/categories",
        data={"name": long_name, "color": "#AABBCC"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "50 characters" in response.text.lower() or "fewer" in response.text.lower()


@pytest.mark.asyncio
async def test_duplicate_category_name_case_insensitive(
    admin_client: httpx.AsyncClient,
    test_categories: list[Category],
):
    existing_name = test_categories[0].name
    upper_name = existing_name.upper()

    response = await admin_client.post(
        "/categories",
        data={"name": upper_name, "color": "#AABBCC"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "already exists" in response.text