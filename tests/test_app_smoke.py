from pathlib import Path

from polyfootballbot.app import NullExchangeClient, build_scheduler, create_app
from polyfootballbot.config import load_settings


class FakeLiveClient:
    pass


def test_create_app_initializes_sqlite(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "smoke.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))
    monkeypatch.setenv("APP_MODE", "dry-run")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    scheduler = create_app()

    assert scheduler.tasks
    assert db_file.exists()


def test_build_scheduler_uses_safe_null_client_in_dry_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "dry.db"))
    monkeypatch.setenv("APP_MODE", "dry-run")
    settings = load_settings()

    scheduler = build_scheduler(settings)
    dry_run_client = scheduler.tasks[1].action.__self__.clob.client

    assert isinstance(dry_run_client, NullExchangeClient)


def test_build_scheduler_uses_real_live_client_builder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "live.db"))
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("FUNDER", "0xdef")
    settings = load_settings()

    monkeypatch.setattr("polyfootballbot.app.build_live_exchange_client", lambda s: FakeLiveClient())
    scheduler = build_scheduler(settings)
    live_client = scheduler.tasks[1].action.__self__.clob.client

    assert isinstance(live_client, FakeLiveClient)
    assert not isinstance(live_client, NullExchangeClient)


def test_build_scheduler_fails_loudly_when_live_client_init_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "live-fail.db"))
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("FUNDER", "0xdef")
    settings = load_settings()

    def _raise(_settings):
        raise RuntimeError("boom")

    monkeypatch.setattr("polyfootballbot.app.build_live_exchange_client", _raise)

    import pytest

    with pytest.raises(RuntimeError, match="boom"):
        build_scheduler(settings)
