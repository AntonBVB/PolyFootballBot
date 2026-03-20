from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from .db import Database
from .gamma import GammaClient, normalize_market

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryService:
    db: Database
    gamma: GammaClient
    open_window_hours: int

    def run(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        deadline = now + timedelta(hours=self.open_window_hours)
        count = 0
        for payload in self.gamma.fetch_soccer_markets():
            bundle = normalize_market(payload)
            if bundle is None:
                continue
            if not bundle.market.enable_orderbook:
                continue
            if not (now < bundle.event.start_time <= deadline):
                continue
            self.db.upsert_discovery_bundle(bundle)
            count += 1
        logger.info("DISCOVERY_OK count=%s", count)
        return count
