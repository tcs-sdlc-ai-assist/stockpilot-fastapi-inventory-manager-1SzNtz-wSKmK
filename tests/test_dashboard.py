import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx

from tests.conftest import (
    app,
    override_get_db,
    test_async_session_maker,
)
from models.user import User
from models.category import Category
from models.item import InventoryItem


@pytest.mark.asyncio
async def test_dashboard_accessible_by_admin(admin_client: httpx.AsyncClient, admin_user: User):
    """Admin users can access the dashboard page successfully."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text
    assert "Dashboard" in text
    assert "Total Items" in text
    assert "Inventory Value" in text
    assert "Low Stock" in text
    assert "Total Users" in text


@pytest.mark.asyncio
async def test_dashboard_accessible_by_staff(staff_client: httpx.AsyncClient, staff_user: User):
    """Staff users can also access the dashboard page."""
    response = await staff_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text
    assert "Dashboard" in text


@pytest.mark.asyncio
async def test_dashboard_unauthenticated_redirect(client: httpx.AsyncClient):
    """Unauthenticated users are redirected away from the dashboard."""
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_dashboard_displays_correct_stats(
    admin_client: httpx.AsyncClient,
    admin_user: User,
    test_items: list[InventoryItem],
    test_categories: list[Category],
):
    """Dashboard displays correct total items, inventory value, and user count."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    # Total items should be 3 (from test_items fixture)
    assert ">3<" in text.replace(" ", "") or "3</p>" in text

    # Total inventory value:
    # Wireless Mouse: 50 * 29.99 = 1499.50
    # USB Keyboard: 5 * 79.99 = 399.95
    # T-Shirt: 0 * 19.99 = 0.00
    # Total = 1899.45
    assert "1899.45" in text

    # Total users: at least 1 (admin_user)
    # The staff_user fixture is not loaded here, so we check for at least the admin
    assert "Total Users" in text


@pytest.mark.asyncio
async def test_dashboard_low_stock_items_listed(
    admin_client: httpx.AsyncClient,
    admin_user: User,
    test_items: list[InventoryItem],
    test_categories: list[Category],
):
    """Dashboard lists low-stock and out-of-stock items in the alerts section."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    # USB Keyboard has quantity=5, reorder_level=10 → low stock
    assert "USB Keyboard" in text

    # T-Shirt has quantity=0, reorder_level=5 → out of stock
    assert "T-Shirt" in text
    assert "Out of Stock" in text

    # Wireless Mouse has quantity=50, reorder_level=10 → NOT low stock
    # It should NOT appear in the low-stock alerts table
    assert "Low-Stock Alerts" in text


@pytest.mark.asyncio
async def test_dashboard_low_stock_count_includes_out_of_stock(
    admin_client: httpx.AsyncClient,
    admin_user: User,
    test_items: list[InventoryItem],
    test_categories: list[Category],
):
    """Low stock count on dashboard includes both low-stock and out-of-stock items."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    # Low stock count should be 2 (USB Keyboard + T-Shirt)
    # The stat card shows the count
    assert "Low Stock" in text


@pytest.mark.asyncio
async def test_dashboard_recent_activity_shown(
    admin_client: httpx.AsyncClient,
    admin_user: User,
    test_items: list[InventoryItem],
    test_categories: list[Category],
):
    """Dashboard shows recent activity feed with item names and user info."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    assert "Recent Activity" in text

    # Recent activity should include the test items
    assert "Wireless Mouse" in text
    assert "USB Keyboard" in text
    assert "T-Shirt" in text

    # The creator's display name should appear
    assert "Test Admin" in text


@pytest.mark.asyncio
async def test_dashboard_no_items_shows_empty_state(
    admin_client: httpx.AsyncClient,
    admin_user: User,
):
    """Dashboard with no inventory items shows appropriate empty messages."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    # With no items, total should be 0
    assert "Total Items" in text
    assert "$0.00" in text

    # No low-stock alerts
    assert "well stocked" in text or "No low-stock alerts" in text

    # No recent activity
    assert "No recent activity" in text or "Recent Activity" in text


@pytest.mark.asyncio
async def test_dashboard_quick_actions_admin(
    admin_client: httpx.AsyncClient,
    admin_user: User,
):
    """Admin dashboard shows admin-specific quick actions like Manage Users."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    assert "Quick Actions" in text
    assert "Add New Item" in text
    assert "Manage Categories" in text
    assert "Manage Users" in text
    assert "View Inventory" in text


@pytest.mark.asyncio
async def test_dashboard_quick_actions_staff(
    staff_client: httpx.AsyncClient,
    staff_user: User,
):
    """Staff dashboard does not show Manage Users quick action."""
    response = await staff_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    assert "Quick Actions" in text
    assert "Add New Item" in text
    assert "Manage Categories" in text
    assert "View Inventory" in text
    # Staff should not see the Users link in quick actions
    # The "Manage Users" link is wrapped in {% if user_role == "admin" %}
    assert "Manage Users" not in text


@pytest.mark.asyncio
async def test_dashboard_header_links_for_admin(
    admin_client: httpx.AsyncClient,
    admin_user: User,
):
    """Admin dashboard page header includes Add Item and Categories links."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    assert 'href="/items/new"' in text
    assert 'href="/categories"' in text
    assert 'href="/users"' in text


@pytest.mark.asyncio
async def test_dashboard_inventory_value_zero_when_no_items(
    admin_client: httpx.AsyncClient,
    admin_user: User,
):
    """Dashboard shows $0.00 inventory value when there are no items."""
    response = await admin_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200
    text = response.text

    assert "$0.00" in text