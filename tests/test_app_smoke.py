from pathlib import Path

import pytest

from polyfootballbot.app import NullExchangeClient, create_app


def test_create_app_initializes_sqlite(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "smoke.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))
    monkeypatch.setenv("APP_MODE", "dry-run")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    scheduler = create_app()

    assert scheduler.tasks
    assert db_file.exists()


def test_live_create_app_raises_when_real_client_init_fails(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "live.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("FUNDER", "0xdef")

    class BrokenClient:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr("py_clob_client.client.ClobClient", BrokenClient)

    with pytest.raises(RuntimeError, match="boom"):
        create_app()


def test_live_path_uses_supplied_exchange_client(tmp_path: Path, monkeypatch) -> None:
    from polyfootballbot.app import build_scheduler
    from polyfootballbot.config import load_settings

    db_file = tmp_path / "live-supplied.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("FUNDER", "0xdef")

    settings = load_settings()
    scheduler = build_scheduler(settings, exchange_client=NullExchangeClient())

    assert scheduler.tasks
    assert db_file.exists()
