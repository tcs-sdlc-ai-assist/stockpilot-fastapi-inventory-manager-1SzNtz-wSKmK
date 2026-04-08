import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.auth import router as auth_router
from routes.inventory import router as inventory_router
from routes.categories import router as categories_router
from routes.users import router as users_router
from routes.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "inventory_router",
    "categories_router",
    "users_router",
    "dashboard_router",
]