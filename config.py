import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class _Settings:
    SECRET_KEY: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    ADMIN_DISPLAY_NAME: str
    DATABASE_URL: str
    DEBUG: bool

    def __init__(self) -> None:
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "")
        self.ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
        self.ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
        self.ADMIN_DISPLAY_NAME = os.environ.get("ADMIN_DISPLAY_NAME", "Admin")
        self.DATABASE_URL = os.environ.get(
            "DATABASE_URL", "sqlite+aiosqlite:///./stockpilot.db"
        )
        self.DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

    def validate(self) -> None:
        missing: list[str] = []

        if not self.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not self.ADMIN_USERNAME:
            missing.append("ADMIN_USERNAME")
        if not self.ADMIN_PASSWORD:
            missing.append("ADMIN_PASSWORD")

        if missing:
            msg = (
                f"Missing critical environment variables: {', '.join(missing)}. "
                "Set them in your .env file or environment before starting the application."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        logger.info("Configuration validated successfully.")


settings = _Settings()