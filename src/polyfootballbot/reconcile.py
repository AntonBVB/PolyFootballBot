from __future__ import annotations

from dataclasses import dataclass
import logging

from .clob import CLOBGateway
from .db import Database
from .models import OrderStatus

logger = logging.getLogger(__name__)


@dataclass
class ReconcileService:
    db: Database
    clob: CLOBGateway

    def run(self) -> int:
        updated = 0
        for row in self.db.list_open_orders(dry_run=self.clob.dry_run):
            if self.clob.dry_run:
                self.db.update_order_status(row["order_id"], OrderStatus.FILLED, float(row["size"]), {"simulated": True})
                updated += 1
                continue
            exchange_order = self.clob.fetch_order_status(row["order_id"])
            self.db.update_order_status(row["order_id"], exchange_order.status, exchange_order.filled_size, exchange_order.payload)
            updated += 1
        logger.info("RECONCILE_UPDATED count=%s", updated)
        return updated
