from __future__ import annotations

import logging
from pathlib import Path

from .clob import CLOBGateway
from .config import Settings, load_settings
from .db import Database
from .gamma import GammaClient
from .logging_setup import configure_logging
from .reconcile import ReconcileService
from .scheduler import ScheduledTask, Scheduler
from .services import DiscoveryService
from .strategy import EntryEngine, ExitEngine

logger = logging.getLogger(__name__)


class NullExchangeClient:
    def get_balance_allowance(self, params):
        return {"available": 100.0}

    def create_order(self, order_args):
        return {"id": f"sim-{order_args['token_id']}"}

    def post_order(self, signed_order, order_type="GTC"):
        return {"id": signed_order.get("id", "sim"), "status": "FILLED", "filledSize": 1.0}

    def get_order_book(self, token_id: str):
        return {"bids": [{"price": 0.75, "size": 10}], "asks": [{"price": 0.76, "size": 10}]}

    def get_order(self, order_id: str):
        return {"id": order_id, "status": "FILLED", "filledSize": 1.0}



def build_scheduler(settings: Settings, exchange_client=None) -> Scheduler:
    configure_logging(settings.log_level)
    repo_root = Path(__file__).resolve().parents[2]
    db = Database(settings.sqlite_path, repo_root / "db" / "schema.sql")
    exchange_client = exchange_client or NullExchangeClient()
    clob = CLOBGateway(
        client=exchange_client,
        signature_type=settings.signature_type,
        funder=settings.funder,
        dry_run=settings.app_mode.value == "dry-run",
    )
    gamma = GammaClient(base_url=settings.gamma_base_url, timeout_seconds=settings.http_timeout_seconds)
    discovery = DiscoveryService(db=db, gamma=gamma, open_window_hours=settings.open_window_hours)
    entry = EntryEngine(settings=settings, db=db, clob=clob)
    exit_engine = ExitEngine(settings=settings, db=db, clob=clob)
    reconcile = ReconcileService(db=db, clob=clob)
    tasks = [
        ScheduledTask("discovery", settings.discovery_seconds, discovery.run),
        ScheduledTask("prematch_entry_scan", settings.prematch_poll_seconds, entry.scan),
        ScheduledTask("fast_scan", settings.fast_poll_seconds, entry.scan),
        ScheduledTask("exit_monitor", settings.fast_poll_seconds, exit_engine.monitor),
        ScheduledTask("reconcile", settings.reconcile_seconds, reconcile.run),
    ]
    logger.info("APP_STARTED mode=%s sqlite_path=%s", settings.app_mode.value, settings.sqlite_path)
    return Scheduler(tasks=tasks)



def create_app() -> Scheduler:
    return build_scheduler(load_settings())



def main() -> None:
    create_app().run_forever()
