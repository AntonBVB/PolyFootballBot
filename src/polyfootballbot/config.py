from dataclasses import dataclass
from pathlib import Path
import os


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_ALLOWED_MODES = {"dry-run", "live"}
_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class Settings:
    app_mode: str = "dry-run"
    scheduler_interval_seconds: int = 30
    sqlite_path: Path = Path("data/polyfootballbot.db")
    log_level: str = "INFO"


class ConfigError(ValueError):
    pass


def load_settings() -> Settings:
    _load_dotenv()

    app_mode = os.getenv("APP_MODE", "dry-run")
    interval_raw = os.getenv("SCHEDULER_INTERVAL_SECONDS", "30")
    sqlite_path = Path(os.getenv("SQLITE_PATH", "data/polyfootballbot.db"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    if app_mode not in _ALLOWED_MODES:
        raise ConfigError(f"APP_MODE must be one of {_ALLOWED_MODES}, got {app_mode}")

    try:
        interval = int(interval_raw)
    except ValueError as exc:
        raise ConfigError(f"SCHEDULER_INTERVAL_SECONDS must be an int, got {interval_raw}") from exc

    if interval < 1:
        raise ConfigError("SCHEDULER_INTERVAL_SECONDS must be >= 1")

    if log_level not in _ALLOWED_LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL must be one of {_ALLOWED_LOG_LEVELS}, got {log_level}")

    return Settings(
        app_mode=app_mode,
        scheduler_interval_seconds=interval,
        sqlite_path=sqlite_path,
        log_level=log_level,
    )
