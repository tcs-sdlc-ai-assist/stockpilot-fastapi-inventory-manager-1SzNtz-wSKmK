import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx

from dependencies import COOKIE_NAME


@pytest.mark.asyncio
async def test_login_page_renders(client: httpx.AsyncClient):
    response = await client.get("/auth/login")
    assert response.status_code == 200
    assert "Welcome back" in response.text
    assert "Sign in" in response.text


@pytest.mark.asyncio
async def test_login_success_admin(client: httpx.AsyncClient, admin_user):
    response = await client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_success_staff(client: httpx.AsyncClient, staff_user):
    response = await client.post(
        "/auth/login",
        data={"username": "teststaff", "password": "staffpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/items"
    assert COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: httpx.AsyncClient, admin_user):
    response = await client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/login",
        data={"username": "nosuchuser", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text


@pytest.mark.asyncio
async def test_login_empty_username(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/login",
        data={"username": "", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username is required" in response.text


@pytest.mark.asyncio
async def test_login_empty_password(client: httpx.AsyncClient, admin_user):
    response = await client.post(
        "/auth/login",
        data={"username": "testadmin", "password": ""},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Password is required" in response.text


@pytest.mark.asyncio
async def test_register_page_renders(client: httpx.AsyncClient):
    response = await client.get("/auth/register")
    assert response.status_code == 200
    assert "Create an Account" in response.text


@pytest.mark.asyncio
async def test_register_success(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "username": "newuser",
            "display_name": "New User",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/items"
    assert COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_register_duplicate_username(client: httpx.AsyncClient, staff_user):
    response = await client.post(
        "/auth/register",
        data={
            "username": "teststaff",
            "display_name": "Another Staff",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "already taken" in response.text


@pytest.mark.asyncio
async def test_register_mismatched_passwords(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "username": "mismatchuser",
            "display_name": "Mismatch User",
            "password": "password123",
            "confirm_password": "differentpassword",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Passwords do not match" in response.text


@pytest.mark.asyncio
async def test_register_short_username(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "username": "ab",
            "display_name": "Short User",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 3 characters" in response.text


@pytest.mark.asyncio
async def test_register_short_password(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "username": "shortpwduser",
            "display_name": "Short Pwd",
            "password": "abc",
            "confirm_password": "abc",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 6 characters" in response.text


@pytest.mark.asyncio
async def test_register_invalid_username_chars(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "username": "bad user!",
            "display_name": "Bad Chars",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "letters, numbers, and underscores" in response.text


@pytest.mark.asyncio
async def test_register_empty_display_name(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "username": "nodisplay",
            "display_name": "",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name is required" in response.text


@pytest.mark.asyncio
async def test_logout_clears_session(admin_client: httpx.AsyncClient):
    response = await admin_client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    cookie_header = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in cookie_header


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_admin(admin_client: httpx.AsyncClient):
    response = await admin_client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_staff(staff_client: httpx.AsyncClient):
    response = await staff_client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/items"


@pytest.mark.asyncio
async def test_register_page_redirects_authenticated_admin(admin_client: httpx.AsyncClient):
    response = await admin_client.get("/auth/register", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


@pytest.mark.asyncio
async def test_register_page_redirects_authenticated_staff(staff_client: httpx.AsyncClient):
    response = await staff_client.get("/auth/register", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/items"


@pytest.mark.asyncio
async def test_registered_user_has_staff_role(client: httpx.AsyncClient, db_session):
    from models.user import User

    response = await client.post(
        "/auth/register",
        data={
            "username": "rolecheck",
            "display_name": "Role Check",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    user = await User.get_by_username(db_session, "rolecheck")
    assert user is not None
    assert user.role == "staff"
    assert user.display_name == "Role Check"


@pytest.mark.asyncio
async def test_registered_user_password_is_hashed(client: httpx.AsyncClient, db_session):
    from models.user import User

    await client.post(
        "/auth/register",
        data={
            "username": "hashcheck",
            "display_name": "Hash Check",
            "password": "myplainpassword",
            "confirm_password": "myplainpassword",
        },
        follow_redirects=False,
    )

    user = await User.get_by_username(db_session, "hashcheck")
    assert user is not None
    assert user.hashed_password != "myplainpassword"
    assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")


@pytest.mark.asyncio
async def test_admin_user_fixture_is_admin(admin_user):
    assert admin_user.role == "admin"
    assert admin_user.is_admin is True
    assert admin_user.username == "testadmin"


@pytest.mark.asyncio
async def test_staff_user_fixture_is_staff(staff_user):
    assert staff_user.role == "staff"
    assert staff_user.is_admin is False
    assert staff_user.username == "teststaff"