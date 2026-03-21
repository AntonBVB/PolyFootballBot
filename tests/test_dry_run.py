from datetime import datetime, timedelta, timezone
from pathlib import Path

from polyfootballbot.db import Database
from polyfootballbot.gamma import normalize_market


def test_dry_run_records_do_not_block_live(tmp_path: Path) -> None:
    db = Database(tmp_path / "bot.db", Path("db/schema.sql"))
    payload = {
        "id": "m1",
        "question": "Will Team A win on 2026-03-21?",
        "slug": "team-a-win",
        "volume": 25000,
        "minimum_tick_size": 0.01,
        "enableOrderBook": True,
        "clobTokenIds": ["yes-1", "no-1"],
        "outcomes": [{"name": "Yes", "clobTokenId": "yes-1", "noTokenId": "no-1"}],
        "event": {
            "id": "e1",
            "homeTeam": "Team A",
            "awayTeam": "Team B",
            "startDate": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "seriesSlug": "soccer",
        },
    }
    bundle = normalize_market(payload)
    assert bundle is not None
    db.upsert_discovery_bundle(bundle)

    assert db.has_open_order_or_position("m1", "no-1", dry_run=True) is False
    assert db.has_open_order_or_position("m1", "no-1", dry_run=False) is False
