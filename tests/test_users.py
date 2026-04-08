import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx

from models.user import User


@pytest.mark.asyncio
async def test_admin_can_list_users(admin_client: httpx.AsyncClient, admin_user: User):
    response = await admin_client.get("/users", follow_redirects=False)
    assert response.status_code == 200
    assert "User Management" in response.text
    assert admin_user.username in response.text


@pytest.mark.asyncio
async def test_admin_can_list_users_shows_all_users(
    admin_client: httpx.AsyncClient,
    admin_user: User,
    staff_user: User,
):
    response = await admin_client.get("/users", follow_redirects=False)
    assert response.status_code == 200
    assert admin_user.username in response.text
    assert staff_user.username in response.text


@pytest.mark.asyncio
async def test_admin_can_add_user(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users",
        data={
            "username": "newuser",
            "display_name": "New User",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users"

    list_response = await admin_client.get("/users", follow_redirects=False)
    assert list_response.status_code == 200
    assert "newuser" in list_response.text


@pytest.mark.asyncio
async def test_admin_can_add_admin_user(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users",
        data={
            "username": "newadmin",
            "display_name": "New Admin",
            "password": "password123",
            "role": "admin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    list_response = await admin_client.get("/users", follow_redirects=False)
    assert list_response.status_code == 200
    assert "newadmin" in list_response.text


@pytest.mark.asyncio
async def test_duplicate_username_rejected(
    admin_client: httpx.AsyncClient,
    staff_user: User,
):
    response = await admin_client.post(
        "/users",
        data={
            "username": staff_user.username,
            "display_name": "Duplicate User",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "already taken" in response.text


@pytest.mark.asyncio
async def test_add_user_short_username_rejected(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users",
        data={
            "username": "ab",
            "display_name": "Short Username",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 3 characters" in response.text


@pytest.mark.asyncio
async def test_add_user_short_password_rejected(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users",
        data={
            "username": "validuser",
            "display_name": "Valid User",
            "password": "12345",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 6 characters" in response.text


@pytest.mark.asyncio
async def test_add_user_missing_display_name_rejected(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users",
        data={
            "username": "validuser2",
            "display_name": "",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name is required" in response.text


@pytest.mark.asyncio
async def test_add_user_invalid_role_rejected(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users",
        data={
            "username": "validuser3",
            "display_name": "Valid User",
            "password": "password123",
            "role": "superadmin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "admin" in response.text.lower() or "staff" in response.text.lower()


@pytest.mark.asyncio
async def test_admin_can_delete_user(
    admin_client: httpx.AsyncClient,
    staff_user: User,
):
    response = await admin_client.post(
        f"/users/{staff_user.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users"

    list_response = await admin_client.get("/users", follow_redirects=False)
    assert list_response.status_code == 200
    assert staff_user.username not in list_response.text


@pytest.mark.asyncio
async def test_delete_nonexistent_user(admin_client: httpx.AsyncClient):
    response = await admin_client.post(
        "/users/99999/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users"


@pytest.mark.asyncio
async def test_default_admin_cannot_be_deleted(
    admin_client: httpx.AsyncClient,
    db_session,
):
    from config import settings

    existing = await User.get_by_username(db_session, settings.ADMIN_USERNAME)
    if existing is None:
        import bcrypt

        hashed = bcrypt.hashpw(
            settings.ADMIN_PASSWORD.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")
        default_admin = User(
            username=settings.ADMIN_USERNAME,
            display_name=settings.ADMIN_DISPLAY_NAME,
            hashed_password=hashed,
            role="admin",
        )
        db_session.add(default_admin)
        await db_session.commit()
        await db_session.refresh(default_admin)
        existing = default_admin

    response = await admin_client.post(
        f"/users/{existing.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    list_response = await admin_client.get("/users", follow_redirects=False)
    assert list_response.status_code == 200
    assert settings.ADMIN_USERNAME in list_response.text


@pytest.mark.asyncio
async def test_self_deletion_prevented(
    admin_client: httpx.AsyncClient,
    admin_user: User,
):
    response = await admin_client.post(
        f"/users/{admin_user.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303

    list_response = await admin_client.get("/users", follow_redirects=False)
    assert list_response.status_code == 200
    assert admin_user.username in list_response.text


@pytest.mark.asyncio
async def test_staff_cannot_access_user_list(staff_client: httpx.AsyncClient):
    response = await staff_client.get("/users", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_staff_cannot_create_user(staff_client: httpx.AsyncClient):
    response = await staff_client.post(
        "/users",
        data={
            "username": "sneakyuser",
            "display_name": "Sneaky User",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_staff_cannot_delete_user(
    staff_client: httpx.AsyncClient,
    admin_user: User,
):
    response = await staff_client.post(
        f"/users/{admin_user.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_unauthenticated_user_redirected_from_user_list(
    client: httpx.AsyncClient,
):
    response = await client.get("/users", follow_redirects=False)
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_unauthenticated_user_redirected_from_create_user(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/users",
        data={
            "username": "anonuser",
            "display_name": "Anon User",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_unauthenticated_user_redirected_from_delete_user(
    client: httpx.AsyncClient,
):
    response = await client.post(
        "/users/1/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303