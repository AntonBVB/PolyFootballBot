import pytest

from polyfootballbot.config import ConfigError, load_settings


def test_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.delenv("SCHEDULER_INTERVAL_SECONDS", raising=False)
    settings = load_settings()
    assert settings.app_mode in {"dry-run", "live"}
    assert settings.scheduler_interval_seconds >= 1


def test_invalid_mode_rejected(monkeypatch) -> None:
    monkeypatch.setenv("APP_MODE", "paper")
    with pytest.raises(ConfigError):
        load_settings()
