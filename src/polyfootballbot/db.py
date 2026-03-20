from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from .models import DiscoveryBundle, ExchangeOrder, MarketFormat, OrderIntent, OrderKind, OrderSide, OrderStatus, OutcomeRole, PositionRecord, PositionStatus, TradeableOutcome


class Database:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path
        self.init_sqlite()

    def init_sqlite(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(self.schema_path.read_text(encoding="utf-8"))

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_discovery_bundle(self, bundle: DiscoveryBundle) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events (event_id, league_name, home_team, away_team, start_time, raw_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(event_id) DO UPDATE SET
                    league_name=excluded.league_name,
                    home_team=excluded.home_team,
                    away_team=excluded.away_team,
                    start_time=excluded.start_time,
                    raw_json=excluded.raw_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    bundle.event.event_id,
                    bundle.event.league_name,
                    bundle.event.home_team,
                    bundle.event.away_team,
                    bundle.event.start_time.isoformat(),
                    bundle.event.raw_json,
                ),
            )
            conn.execute(
                """
                INSERT INTO markets (market_id, event_id, question, slug, market_type, market_format, total_volume, tick_size,
                    neg_risk, enable_orderbook, active, closed, archived, live, raw_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(market_id) DO UPDATE SET
                    question=excluded.question,
                    slug=excluded.slug,
                    market_type=excluded.market_type,
                    market_format=excluded.market_format,
                    total_volume=excluded.total_volume,
                    tick_size=excluded.tick_size,
                    neg_risk=excluded.neg_risk,
                    enable_orderbook=excluded.enable_orderbook,
                    active=excluded.active,
                    closed=excluded.closed,
                    archived=excluded.archived,
                    live=excluded.live,
                    raw_json=excluded.raw_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    bundle.market.market_id,
                    bundle.market.event_id,
                    bundle.market.question,
                    bundle.market.slug,
                    bundle.market.market_type.value,
                    bundle.market.market_format.value,
                    bundle.market.total_volume,
                    bundle.market.tick_size,
                    int(bundle.market.neg_risk),
                    int(bundle.market.enable_orderbook),
                    int(bundle.market.active),
                    int(bundle.market.closed),
                    int(bundle.market.archived),
                    int(bundle.market.live),
                    bundle.market.raw_json,
                ),
            )
            for outcome in bundle.outcomes:
                conn.execute(
                    """
                    INSERT INTO outcomes (outcome_id, market_id, outcome_name, outcome_role, token_id, no_token_id,
                        is_tradeable, raw_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(outcome_id) DO UPDATE SET
                        outcome_name=excluded.outcome_name,
                        outcome_role=excluded.outcome_role,
                        token_id=excluded.token_id,
                        no_token_id=excluded.no_token_id,
                        is_tradeable=excluded.is_tradeable,
                        raw_json=excluded.raw_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        outcome.outcome_id,
                        outcome.market_id,
                        outcome.outcome_name,
                        outcome.outcome_role.value,
                        outcome.token_id,
                        outcome.no_token_id,
                        int(outcome.is_tradeable),
                        outcome.raw_json,
                    ),
                )

    def list_tradeable_outcomes(self, dry_run: bool) -> list[TradeableOutcome]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT o.market_id, m.event_id, e.start_time, m.market_type, m.market_format, o.outcome_name, o.outcome_role,
                       o.token_id, o.no_token_id, m.tick_size, m.total_volume, m.enable_orderbook, m.live
                FROM outcomes o
                JOIN markets m ON m.market_id = o.market_id
                JOIN events e ON e.event_id = m.event_id
                WHERE o.is_tradeable = 1
                  AND m.active = 1
                  AND m.closed = 0
                  AND m.archived = 0
                ORDER BY e.start_time ASC
                """
            ).fetchall()
        return [
            TradeableOutcome(
                market_id=row["market_id"],
                event_id=row["event_id"],
                event_start_time=datetime.fromisoformat(row["start_time"]),
                market_type=row["market_type"],
                market_format=MarketFormat(row["market_format"]),
                outcome_name=row["outcome_name"],
                outcome_role=OutcomeRole(row["outcome_role"]),
                token_id=row["token_id"],
                no_token_id=row["no_token_id"],
                tick_size=float(row["tick_size"]),
                total_volume=float(row["total_volume"]),
                enable_orderbook=bool(row["enable_orderbook"]),
                live=bool(row["live"]),
            )
            for row in rows
        ]

    def has_open_order_or_position(self, market_id: str, token_id: str, dry_run: bool) -> bool:
        dry_run_value = 1 if dry_run else 0
        with self.connect() as conn:
            order_exists = conn.execute(
                """
                SELECT 1 FROM orders
                WHERE market_id = ? AND token_id = ? AND dry_run = ? AND status = 'OPEN'
                LIMIT 1
                """,
                (market_id, token_id, dry_run_value),
            ).fetchone()
            position_exists = conn.execute(
                """
                SELECT 1 FROM positions
                WHERE market_id = ? AND token_id = ? AND dry_run = ? AND status IN ('OPEN', 'CLOSING', 'EXIT_PENDING')
                LIMIT 1
                """,
                (market_id, token_id, dry_run_value),
            ).fetchone()
        return bool(order_exists or position_exists)

    def record_order(self, intent: OrderIntent, result: ExchangeOrder) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO orders (order_id, market_id, token_id, outcome_name, outcome_role, market_format, kind, side,
                    price, size, filled_size, status, dry_run, created_at, updated_at, exchange_payload_json, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    filled_size=excluded.filled_size,
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP,
                    exchange_payload_json=excluded.exchange_payload_json,
                    error_message=excluded.error_message
                """,
                (
                    result.order_id,
                    intent.market_id,
                    intent.token_id,
                    intent.outcome_name,
                    intent.outcome_role.value,
                    intent.market_format.value,
                    intent.kind.value,
                    intent.side.value,
                    intent.price,
                    intent.size,
                    result.filled_size,
                    result.status.value,
                    int(intent.dry_run),
                    json.dumps(result.payload, sort_keys=True),
                    result.error_message,
                ),
            )

    def open_position_from_fill(self, intent: OrderIntent, result: ExchangeOrder) -> None:
        if result.filled_size <= 0:
            return
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO positions (market_id, token_id, outcome_name, outcome_role, market_format, shares, entry_price,
                    status, opened_at, notes, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', CURRENT_TIMESTAMP, ?, ?)
                """,
                (
                    intent.market_id,
                    intent.token_id,
                    intent.outcome_name,
                    intent.outcome_role.value,
                    intent.market_format.value,
                    result.filled_size,
                    intent.price,
                    f"Opened from {intent.kind.value}",
                    int(intent.dry_run),
                ),
            )

    def list_open_positions(self, dry_run: bool) -> list[PositionRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT position_id, market_id, token_id, outcome_name, outcome_role, market_format, shares, entry_price,
                       status, opened_at, closed_at, live_detected_at, notes, dry_run
                FROM positions
                WHERE dry_run = ? AND status IN ('OPEN', 'CLOSING', 'EXIT_PENDING')
                ORDER BY opened_at ASC
                """,
                (1 if dry_run else 0,),
            ).fetchall()
        return [
            PositionRecord(
                position_id=row["position_id"],
                market_id=row["market_id"],
                token_id=row["token_id"],
                outcome_name=row["outcome_name"],
                outcome_role=OutcomeRole(row["outcome_role"]),
                market_format=MarketFormat(row["market_format"]),
                shares=float(row["shares"]),
                entry_price=float(row["entry_price"]),
                status=PositionStatus(row["status"]),
                opened_at=datetime.fromisoformat(row["opened_at"]) if row["opened_at"] else None,
                closed_at=datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None,
                live_detected_at=datetime.fromisoformat(row["live_detected_at"]) if row["live_detected_at"] else None,
                notes=row["notes"],
                dry_run=bool(row["dry_run"]),
            )
            for row in rows
        ]

    def mark_position_status(self, position_id: int, status: PositionStatus, notes: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE positions SET status = ?, notes = COALESCE(?, notes), closed_at = CASE WHEN ? = 'CLOSED' THEN CURRENT_TIMESTAMP ELSE closed_at END WHERE position_id = ?",
                (status.value, notes, status.value, position_id),
            )

    def list_open_orders(self, dry_run: bool) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM orders WHERE dry_run = ? AND status = 'OPEN' ORDER BY created_at ASC",
                (1 if dry_run else 0,),
            ).fetchall()

    def update_order_status(self, order_id: str, status: OrderStatus, filled_size: float, payload: dict[str, object]) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE orders SET status = ?, filled_size = ?, exchange_payload_json = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                (status.value, filled_size, json.dumps(payload, sort_keys=True), order_id),
            )
