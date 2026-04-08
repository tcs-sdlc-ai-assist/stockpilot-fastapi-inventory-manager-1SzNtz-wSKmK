import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import settings
from database import init_db
from dependencies import get_current_user
from models.user import User
from seed import run_seeding

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings.validate()
    logger.info("Starting StockPilot application...")
    await init_db()
    await run_seeding()
    logger.info("StockPilot application started successfully.")
    yield
    logger.info("StockPilot application shutting down.")


app = FastAPI(
    title="StockPilot",
    description="Modern Inventory Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

from routes.auth import router as auth_router
from routes.categories import router as categories_router
from routes.dashboard import router as dashboard_router
from routes.inventory import router as inventory_router
from routes.users import router as users_router

app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(categories_router)
app.include_router(users_router)
app.include_router(dashboard_router)


@app.get("/")
async def landing_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    return templates.TemplateResponse(
        request,
        "landing.html",
        context={
            "current_user": current_user,
            "user_role": current_user.role if current_user else None,
            "flash_messages": [],
        },
    )


@app.get("/login")
async def login_redirect(request: Request) -> Response:
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/login", status_code=303)


@app.get("/register")
async def register_redirect(request: Request) -> Response:
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/register", status_code=303)


@app.get("/logout")
async def logout_redirect(request: Request) -> Response:
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/auth/logout", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> Response:
    if exc.status_code == 404:
        from database import get_db as _get_db

        current_user = None
        try:
            async for db in _get_db():
                current_user = await get_current_user(request, db)
                break
        except Exception:
            current_user = None

        return templates.TemplateResponse(
            request,
            "errors/404.html",
            context={
                "current_user": current_user,
                "user_role": current_user.role if current_user else None,
                "flash_messages": [],
            },
            status_code=404,
        )

    if exc.status_code == 303:
        from fastapi.responses import RedirectResponse

        if "login" in str(exc.detail).lower() or "authentication" in str(exc.detail).lower():
            return RedirectResponse(url="/login", status_code=303)
        if "admin" in str(exc.detail).lower():
            return RedirectResponse(url="/dashboard", status_code=303)

    return HTMLResponse(
        content=f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>",
        status_code=exc.status_code,
    )