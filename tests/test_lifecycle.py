from datetime import datetime, timedelta, timezone
from pathlib import Path

from polyfootballbot.clob import CLOBGateway
from polyfootballbot.config import load_settings
from polyfootballbot.db import Database
from polyfootballbot.gamma import normalize_market
from polyfootballbot.models import OrderSide
from polyfootballbot.strategy import EntryEngine, ExitEngine


class StubClient:
    def __init__(self) -> None:
        self.orders = []

    def get_balance_allowance(self, params):
        return {"available": 100}

    def create_order(self, order_args):
        self.orders.append(order_args)
        return {"id": f"order-{len(self.orders)}", **order_args}

    def post_order(self, signed_order, order_type="GTC"):
        return {"id": signed_order["id"], "status": "FILLED", "filledSize": signed_order["size"]}

    def get_order_book(self, token_id: str):
        if len(self.orders) == 0:
            return {"bids": [{"price": 0.74, "size": 10}], "asks": [{"price": 0.75, "size": 10}]}
        return {"bids": [{"price": 0.81, "size": 10}], "asks": [{"price": 0.82, "size": 10}]}

    def get_order(self, order_id: str):
        return {"id": order_id, "status": "FILLED", "filledSize": 1}


def _seed_tradeable_market(db: Database) -> None:
    payload = {
        "id": "m1",
        "question": "Will Team A win on 2026-03-21?",
        "slug": "team-a-win",
        "volume": 25000,
        "minimum_tick_size": 0.01,
        "enableOrderBook": True,
        "clobTokenIds": ["yes-1", "no-1"],
        "outcomes": [{"name": "Team A", "clobTokenId": "yes-1", "noTokenId": "no-1"}],
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


def test_buy_no_then_sell_same_no_token(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "bot.db"))
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("FUNDER", "0xdef")
    settings = load_settings()
    db = Database(settings.sqlite_path, Path("db/schema.sql"))
    _seed_tradeable_market(db)
    client = StubClient()
    clob = CLOBGateway(client=client, signature_type=settings.signature_type, funder=settings.funder, dry_run=False)

    EntryEngine(settings=settings, db=db, clob=clob).scan()
    ExitEngine(settings=settings, db=db, clob=clob).monitor(now=datetime.now(timezone.utc) + timedelta(minutes=1))

    assert len(client.orders) == 2
    assert client.orders[0]["side"] == OrderSide.BUY.value
    assert client.orders[0]["token_id"] == "no-1"
    assert client.orders[1]["side"] == OrderSide.SELL.value
    assert client.orders[1]["token_id"] == "no-1"
