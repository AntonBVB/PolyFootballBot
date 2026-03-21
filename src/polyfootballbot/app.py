from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

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



def build_live_exchange_client(settings: Settings) -> Any:
    try:
        from py_clob_client.client import ClobClient
    except ImportError as exc:  # pragma: no cover - depends on environment package availability
        raise RuntimeError("py_clob_client is required for APP_MODE=live") from exc

    try:
        client = ClobClient(
            host=settings.polymarket_host,
            chain_id=settings.chain_id,
            key=settings.private_key,
            signature_type=settings.signature_type,
            funder=settings.funder,
        )
        api_creds = client.create_or_derive_api_creds()
        client.set_api_creds(api_creds)
        return client
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize live Polymarket client: {exc}") from exc



def select_exchange_client(settings: Settings, exchange_client=None):
    if exchange_client is not None:
        return exchange_client
    if settings.app_mode.value == "dry-run":
        return NullExchangeClient()
    return build_live_exchange_client(settings)



def build_scheduler(settings: Settings, exchange_client=None) -> Scheduler:
    configure_logging(settings.log_level)
    repo_root = Path(__file__).resolve().parents[2]
    db = Database(settings.sqlite_path, repo_root / "db" / "schema.sql")
    exchange_client = select_exchange_client(settings, exchange_client=exchange_client)
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
