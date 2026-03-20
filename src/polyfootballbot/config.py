from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from .models import AppMode


class ConfigError(ValueError):
    pass


_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_REQUIRED_IN_LIVE = ("PRIVATE_KEY", "FUNDER")


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    app_mode: AppMode
    sqlite_path: Path
    log_level: str
    polymarket_host: str
    gamma_base_url: str
    private_key: str | None
    funder: str | None
    signature_type: int
    chain_id: int
    entry_min: float
    entry_max: float
    take_profit_delta: float
    max_spread: float
    min_total_volume: float
    buy_cost_usd: float
    min_available_usdc: float
    open_window_hours: int
    fast_mode_before_start_minutes: int
    prematch_poll_seconds: int
    fast_poll_seconds: int
    discovery_seconds: int
    reconcile_seconds: int
    http_timeout_seconds: float



def _read_float(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a float, got {raw}") from exc



def _read_int(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an int, got {raw}") from exc



def load_settings() -> Settings:
    _load_dotenv()

    mode_raw = os.getenv("APP_MODE", AppMode.DRY_RUN.value)
    try:
        app_mode = AppMode(mode_raw)
    except ValueError as exc:
        raise ConfigError(f"APP_MODE must be one of {[m.value for m in AppMode]}, got {mode_raw}") from exc

    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level not in _ALLOWED_LOG_LEVELS:
        raise ConfigError(f"LOG_LEVEL must be one of {_ALLOWED_LOG_LEVELS}, got {log_level}")

    settings = Settings(
        app_mode=app_mode,
        sqlite_path=Path(os.getenv("SQLITE_PATH", "data/polyfootballbot.db")),
        log_level=log_level,
        polymarket_host=os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com"),
        gamma_base_url=os.getenv("GAMMA_BASE_URL", "https://gamma-api.polymarket.com"),
        private_key=os.getenv("PRIVATE_KEY"),
        funder=os.getenv("FUNDER"),
        signature_type=_read_int("SIGNATURE_TYPE", "2"),
        chain_id=_read_int("CHAIN_ID", "137"),
        entry_min=_read_float("ENTRY_MIN", "0.73"),
        entry_max=_read_float("ENTRY_MAX", "0.83"),
        take_profit_delta=_read_float("TAKE_PROFIT_DELTA", "0.05"),
        max_spread=_read_float("MAX_SPREAD", "0.03"),
        min_total_volume=_read_float("MIN_TOTAL_VOLUME", "20000"),
        buy_cost_usd=_read_float("BUY_COST_USD", "5"),
        min_available_usdc=_read_float("MIN_AVAILABLE_USDC", "6"),
        open_window_hours=_read_int("OPEN_WINDOW_HOURS", "12"),
        fast_mode_before_start_minutes=_read_int("FAST_MODE_BEFORE_START_MINUTES", "3"),
        prematch_poll_seconds=_read_int("PREMATCH_POLL_SECONDS", "60"),
        fast_poll_seconds=_read_int("FAST_POLL_SECONDS", "15"),
        discovery_seconds=_read_int("DISCOVERY_SECONDS", "3600"),
        reconcile_seconds=_read_int("RECONCILE_SECONDS", "600"),
        http_timeout_seconds=_read_float("HTTP_TIMEOUT_SECONDS", "10"),
    )

    if settings.entry_min >= settings.entry_max:
        raise ConfigError("ENTRY_MIN must be lower than ENTRY_MAX")
    if settings.signature_type <= 0:
        raise ConfigError("SIGNATURE_TYPE must be positive")
    if settings.open_window_hours <= 0:
        raise ConfigError("OPEN_WINDOW_HOURS must be positive")

    if settings.app_mode is AppMode.LIVE:
        missing = [name for name in _REQUIRED_IN_LIVE if not os.getenv(name)]
        if missing:
            raise ConfigError(f"Missing required live settings: {', '.join(missing)}")

    return settings
