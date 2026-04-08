import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.item import InventoryItem
from models.category import Category
from models.user import User


class TestListInventory:
    """Tests for GET /items — inventory listing."""

    async def test_list_items_authenticated(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items")
        assert response.status_code == 200
        text = response.text
        assert "Wireless Mouse" in text
        assert "USB Keyboard" in text
        assert "T-Shirt" in text

    async def test_list_items_unauthenticated(
        self,
        client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await client.get("/items")
        assert response.status_code == 200
        text = response.text
        assert "Wireless Mouse" in text

    async def test_list_items_empty(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/items")
        assert response.status_code == 200
        assert "No inventory items found" in response.text

    async def test_list_items_search_by_name(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"search": "Wireless"})
        assert response.status_code == 200
        text = response.text
        assert "Wireless Mouse" in text
        assert "USB Keyboard" not in text

    async def test_list_items_search_by_sku(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"search": "KB-002"})
        assert response.status_code == 200
        text = response.text
        assert "USB Keyboard" in text
        assert "Wireless Mouse" not in text

    async def test_list_items_search_no_results(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"search": "nonexistent_xyz"})
        assert response.status_code == 200
        assert "No inventory items found" in response.text

    async def test_list_items_filter_by_category(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        test_categories: list[Category],
    ):
        electronics_id = test_categories[0].id
        response = await admin_client.get("/items", params={"category": str(electronics_id)})
        assert response.status_code == 200
        text = response.text
        assert "Wireless Mouse" in text
        assert "USB Keyboard" in text
        assert "T-Shirt" not in text

    async def test_list_items_sort_by_name_asc(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"sort": "name_asc"})
        assert response.status_code == 200
        text = response.text
        pos_tshirt = text.find("T-Shirt")
        pos_usb = text.find("USB Keyboard")
        pos_wireless = text.find("Wireless Mouse")
        assert pos_tshirt < pos_usb < pos_wireless

    async def test_list_items_sort_by_name_desc(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"sort": "name_desc"})
        assert response.status_code == 200
        text = response.text
        pos_wireless = text.find("Wireless Mouse")
        pos_usb = text.find("USB Keyboard")
        pos_tshirt = text.find("T-Shirt")
        assert pos_wireless < pos_usb < pos_tshirt

    async def test_list_items_sort_by_quantity_asc(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"sort": "quantity_asc"})
        assert response.status_code == 200
        text = response.text
        pos_tshirt = text.find("T-Shirt")
        pos_keyboard = text.find("USB Keyboard")
        pos_mouse = text.find("Wireless Mouse")
        assert pos_tshirt < pos_keyboard < pos_mouse

    async def test_list_items_sort_by_price_desc(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items", params={"sort": "price_desc"})
        assert response.status_code == 200
        text = response.text
        pos_keyboard = text.find("USB Keyboard")
        pos_mouse = text.find("Wireless Mouse")
        pos_tshirt = text.find("T-Shirt")
        assert pos_keyboard < pos_mouse < pos_tshirt


class TestCreateItem:
    """Tests for GET /items/new and POST /items/add — item creation."""

    async def test_add_item_form_authenticated(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
    ):
        response = await admin_client.get("/items/new")
        assert response.status_code == 200
        assert "Add New Item" in response.text

    async def test_add_item_form_unauthenticated_redirects(
        self,
        client: httpx.AsyncClient,
    ):
        response = await client.get("/items/new", follow_redirects=False)
        assert response.status_code == 303 or response.status_code == 200

    async def test_create_item_success(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "New Test Item",
                "sku": "NTI-001",
                "description": "A brand new test item",
                "category_id": str(test_categories[0].id),
                "quantity": "25",
                "unit_price": "49.99",
                "reorder_level": "5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/items"

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.sku == "NTI-001")
        )
        item = result.scalars().first()
        assert item is not None
        assert item.name == "New Test Item"
        assert item.quantity == 25
        assert item.unit_price == 49.99
        assert item.reorder_level == 5

    async def test_create_item_staff_success(
        self,
        staff_client: httpx.AsyncClient,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        response = await staff_client.post(
            "/items/add",
            data={
                "name": "Staff Created Item",
                "sku": "SCI-001",
                "description": "Created by staff",
                "category_id": str(test_categories[1].id),
                "quantity": "10",
                "unit_price": "15.00",
                "reorder_level": "3",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.sku == "SCI-001")
        )
        item = result.scalars().first()
        assert item is not None
        assert item.name == "Staff Created Item"

    async def test_create_item_missing_name(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "",
                "sku": "FAIL-001",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "Item name is required" in response.text

    async def test_create_item_missing_quantity(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "No Quantity Item",
                "sku": "NQ-001",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "Quantity is required" in response.text

    async def test_create_item_missing_unit_price(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "No Price Item",
                "sku": "NP-001",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "10",
                "unit_price": "",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "Unit price is required" in response.text

    async def test_create_item_missing_category(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "No Category Item",
                "sku": "NC-001",
                "description": "",
                "category_id": "",
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "Category is required" in response.text

    async def test_create_item_negative_quantity(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "Negative Qty Item",
                "sku": "NEG-001",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "-5",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "Quantity must be 0 or greater" in response.text

    async def test_create_item_duplicate_sku(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        test_categories: list[Category],
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "Duplicate SKU Item",
                "sku": "WM-001",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "SKU already exists" in response.text

    async def test_create_item_without_sku(
        self,
        admin_client: httpx.AsyncClient,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            "/items/add",
            data={
                "name": "No SKU Item",
                "sku": "",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.name == "No SKU Item")
        )
        item = result.scalars().first()
        assert item is not None
        assert item.sku is None
        assert item.reorder_level == 10


class TestItemDetail:
    """Tests for GET /items/{item_id} — item detail page."""

    async def test_item_detail_authenticated(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await admin_client.get(f"/items/{item.id}")
        assert response.status_code == 200
        assert item.name in response.text
        assert "WM-001" in response.text

    async def test_item_detail_unauthenticated(
        self,
        client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await client.get(f"/items/{item.id}")
        assert response.status_code == 200
        assert item.name in response.text

    async def test_item_detail_not_found(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/items/99999")
        assert response.status_code == 404

    async def test_item_detail_shows_edit_delete_for_admin(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await admin_client.get(f"/items/{item.id}")
        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Delete" in response.text

    async def test_item_detail_shows_edit_delete_for_owner(
        self,
        staff_client: httpx.AsyncClient,
        staff_user: User,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Owned Item",
            sku="SOI-001",
            quantity=10,
            unit_price=5.00,
            reorder_level=2,
            category_id=test_categories[0].id,
            created_by_id=staff_user.id,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        response = await staff_client.get(f"/items/{item.id}")
        assert response.status_code == 200
        assert "Edit" in response.text
        assert "Delete" in response.text

    async def test_item_detail_no_edit_delete_for_non_owner_staff(
        self,
        staff_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await staff_client.get(f"/items/{item.id}")
        assert response.status_code == 200
        text = response.text
        assert f"/items/{item.id}/edit" not in text


class TestEditItem:
    """Tests for GET /items/{item_id}/edit and POST /items/{item_id}/edit."""

    async def test_edit_item_form_admin(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await admin_client.get(f"/items/{item.id}/edit")
        assert response.status_code == 200
        assert "Edit Item" in response.text
        assert item.name in response.text

    async def test_edit_item_form_owner_staff(
        self,
        staff_client: httpx.AsyncClient,
        staff_user: User,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Edit Item",
            sku="SEI-001",
            quantity=10,
            unit_price=5.00,
            reorder_level=2,
            category_id=test_categories[0].id,
            created_by_id=staff_user.id,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        response = await staff_client.get(f"/items/{item.id}/edit")
        assert response.status_code == 200
        assert "Edit Item" in response.text

    async def test_edit_item_form_non_owner_staff_redirects(
        self,
        staff_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await staff_client.get(f"/items/{item.id}/edit", follow_redirects=False)
        assert response.status_code == 303
        assert f"/items/{item.id}" in response.headers.get("location", "")

    async def test_edit_item_submit_admin(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        item = test_items[0]
        response = await admin_client.post(
            f"/items/{item.id}/edit",
            data={
                "name": "Updated Mouse",
                "sku": "WM-001",
                "description": "Updated description",
                "category_id": str(test_categories[0].id),
                "quantity": "100",
                "unit_price": "39.99",
                "reorder_level": "15",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/items/{item.id}" in response.headers.get("location", "")

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item.id)
        )
        updated_item = result.scalars().first()
        assert updated_item is not None
        assert updated_item.name == "Updated Mouse"
        assert updated_item.quantity == 100
        assert updated_item.unit_price == 39.99

    async def test_edit_item_submit_owner_staff(
        self,
        staff_client: httpx.AsyncClient,
        staff_user: User,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Editable",
            sku="SE-001",
            quantity=10,
            unit_price=5.00,
            reorder_level=2,
            category_id=test_categories[0].id,
            created_by_id=staff_user.id,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        response = await staff_client.post(
            f"/items/{item.id}/edit",
            data={
                "name": "Staff Updated",
                "sku": "SE-001",
                "description": "Updated by staff",
                "category_id": str(test_categories[0].id),
                "quantity": "20",
                "unit_price": "10.00",
                "reorder_level": "5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item.id)
        )
        updated_item = result.scalars().first()
        assert updated_item is not None
        assert updated_item.name == "Staff Updated"
        assert updated_item.quantity == 20

    async def test_edit_item_submit_non_owner_staff_rejected(
        self,
        staff_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        test_categories: list[Category],
    ):
        item = test_items[0]
        response = await staff_client.post(
            f"/items/{item.id}/edit",
            data={
                "name": "Hacked Name",
                "sku": "WM-001",
                "description": "Should not work",
                "category_id": str(test_categories[0].id),
                "quantity": "999",
                "unit_price": "0.01",
                "reorder_level": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/items/{item.id}" in response.headers.get("location", "")

    async def test_edit_item_not_found(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.get("/items/99999/edit")
        assert response.status_code == 404

    async def test_edit_item_submit_validation_error(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        test_categories: list[Category],
    ):
        item = test_items[0]
        response = await admin_client.post(
            f"/items/{item.id}/edit",
            data={
                "name": "",
                "sku": "WM-001",
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "Item name is required" in response.text

    async def test_edit_item_duplicate_sku_rejected(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        test_categories: list[Category],
    ):
        item = test_items[0]
        other_sku = test_items[1].sku
        response = await admin_client.post(
            f"/items/{item.id}/edit",
            data={
                "name": "Updated Mouse",
                "sku": other_sku,
                "description": "",
                "category_id": str(test_categories[0].id),
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
        )
        assert response.status_code == 422
        assert "SKU already exists" in response.text


class TestDeleteItem:
    """Tests for POST /items/{item_id}/delete — item deletion."""

    async def test_delete_item_admin(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        db_session: AsyncSession,
    ):
        item = test_items[0]
        item_id = item.id
        response = await admin_client.post(
            f"/items/{item_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/items"

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        deleted_item = result.scalars().first()
        assert deleted_item is None

    async def test_delete_item_owner_staff(
        self,
        staff_client: httpx.AsyncClient,
        staff_user: User,
        test_categories: list[Category],
        db_session: AsyncSession,
    ):
        item = InventoryItem(
            name="Staff Deletable",
            sku="SD-001",
            quantity=10,
            unit_price=5.00,
            reorder_level=2,
            category_id=test_categories[0].id,
            created_by_id=staff_user.id,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        item_id = item.id

        response = await staff_client.post(
            f"/items/{item_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        deleted_item = result.scalars().first()
        assert deleted_item is None

    async def test_delete_item_non_owner_staff_rejected(
        self,
        staff_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
        db_session: AsyncSession,
    ):
        item = test_items[0]
        item_id = item.id
        response = await staff_client.post(
            f"/items/{item_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/items/{item_id}" in response.headers.get("location", "")

        await db_session.expire_all()
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        still_exists = result.scalars().first()
        assert still_exists is not None

    async def test_delete_item_not_found(
        self,
        admin_client: httpx.AsyncClient,
    ):
        response = await admin_client.post("/items/99999/delete")
        assert response.status_code == 404

    async def test_delete_item_unauthenticated_redirects(
        self,
        client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await client.post(
            f"/items/{item.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestLowStockHighlighting:
    """Tests for low-stock and out-of-stock data in inventory listing."""

    async def test_out_of_stock_item_shown_in_list(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items")
        assert response.status_code == 200
        text = response.text
        assert "Out of Stock" in text

    async def test_low_stock_item_shown_in_list(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items")
        assert response.status_code == 200
        text = response.text
        assert "Low Stock" in text

    async def test_in_stock_item_shown_in_list(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        response = await admin_client.get("/items")
        assert response.status_code == 200
        text = response.text
        assert "In Stock" in text

    async def test_item_detail_out_of_stock_status(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        out_of_stock_item = test_items[2]
        assert out_of_stock_item.quantity == 0
        response = await admin_client.get(f"/items/{out_of_stock_item.id}")
        assert response.status_code == 200
        assert "Out of Stock" in response.text

    async def test_item_detail_low_stock_status(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        low_stock_item = test_items[1]
        assert low_stock_item.quantity == 5
        assert low_stock_item.reorder_level == 10
        response = await admin_client.get(f"/items/{low_stock_item.id}")
        assert response.status_code == 200
        assert "Low Stock" in response.text

    async def test_item_detail_in_stock_status(
        self,
        admin_client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        in_stock_item = test_items[0]
        assert in_stock_item.quantity == 50
        assert in_stock_item.reorder_level == 10
        response = await admin_client.get(f"/items/{in_stock_item.id}")
        assert response.status_code == 200
        assert "In Stock" in response.text


class TestUnauthenticatedAccess:
    """Tests that unauthenticated users are redirected for protected routes."""

    async def test_add_item_form_unauthenticated(
        self,
        client: httpx.AsyncClient,
    ):
        response = await client.get("/items/new", follow_redirects=False)
        assert response.status_code == 303

    async def test_add_item_submit_unauthenticated(
        self,
        client: httpx.AsyncClient,
    ):
        response = await client.post(
            "/items/add",
            data={
                "name": "Unauthorized Item",
                "sku": "UNAUTH-001",
                "description": "",
                "category_id": "1",
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_edit_item_form_unauthenticated(
        self,
        client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await client.get(f"/items/{item.id}/edit", follow_redirects=False)
        assert response.status_code == 303

    async def test_edit_item_submit_unauthenticated(
        self,
        client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await client.post(
            f"/items/{item.id}/edit",
            data={
                "name": "Unauthorized Edit",
                "sku": "WM-001",
                "description": "",
                "category_id": "1",
                "quantity": "10",
                "unit_price": "5.00",
                "reorder_level": "2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_delete_item_unauthenticated(
        self,
        client: httpx.AsyncClient,
        test_items: list[InventoryItem],
    ):
        item = test_items[0]
        response = await client.post(
            f"/items/{item.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303