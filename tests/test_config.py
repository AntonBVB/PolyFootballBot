from pathlib import Path

import pytest
import polyfootballbot.config as config_module
from polyfootballbot.config import ConfigError
from polyfootballbot.models import AppMode


def _disable_dotenv(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "_load_dotenv", lambda path=Path(".env"): None)


def test_settings_defaults(monkeypatch) -> None:
    _disable_dotenv(monkeypatch)
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.delenv("ENTRY_MIN", raising=False)
    settings = config_module.load_settings()
    assert settings.app_mode == AppMode.DRY_RUN
    assert settings.entry_min == 0.73
    assert settings.open_window_hours == 12


def test_invalid_mode_rejected(monkeypatch) -> None:
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("APP_MODE", "paper")
    with pytest.raises(ConfigError):
        config_module.load_settings()


def test_live_requires_credentials(monkeypatch) -> None:
    _disable_dotenv(monkeypatch)
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("FUNDER", raising=False)
    with pytest.raises(ConfigError):
        config_module.load_settings()
