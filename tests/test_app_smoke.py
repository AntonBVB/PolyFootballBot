from pathlib import Path

from polyfootballbot.app import create_app


def test_create_app_initializes_sqlite(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "smoke.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))
    monkeypatch.setenv("APP_MODE", "dry-run")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    scheduler = create_app()

    assert scheduler.settings.sqlite_path == db_file
    assert db_file.exists()
