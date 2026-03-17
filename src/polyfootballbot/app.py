import logging
from pathlib import Path

from .config import load_settings
from .db import init_sqlite
from .logging_setup import configure_logging
from .scheduler import Scheduler

logger = logging.getLogger(__name__)


def create_app() -> Scheduler:
    settings = load_settings()
    configure_logging(settings.log_level)

    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / "db" / "schema.sql"
    init_sqlite(settings.sqlite_path, schema_path)

    logger.info("APP_STARTED mode=%s sqlite_path=%s", settings.app_mode, settings.sqlite_path)
    return Scheduler(settings)


def main() -> None:
    scheduler = create_app()
    scheduler.run_forever()
