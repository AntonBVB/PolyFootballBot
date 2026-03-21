import pytest

from polyfootballbot.config import ConfigError, load_settings
from polyfootballbot.models import AppMode


def test_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.delenv("ENTRY_MIN", raising=False)
    settings = load_settings()
    assert settings.app_mode == AppMode.DRY_RUN
    assert settings.entry_min == 0.73
    assert settings.open_window_hours == 12


def test_invalid_mode_rejected(monkeypatch) -> None:
    monkeypatch.setenv("APP_MODE", "paper")
    with pytest.raises(ConfigError):
        load_settings()


def test_live_requires_credentials(monkeypatch) -> None:
    monkeypatch.setattr("polyfootballbot.config._load_dotenv", lambda path=None: None)
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("FUNDER", raising=False)
    with pytest.raises(ConfigError):
        load_settings()


def test_dry_run_does_not_require_live_credentials(monkeypatch) -> None:
    monkeypatch.setattr("polyfootballbot.config._load_dotenv", lambda path=None: None)
    monkeypatch.setenv("APP_MODE", "dry-run")
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("FUNDER", raising=False)

    settings = load_settings()

    assert settings.app_mode == AppMode.DRY_RUN
