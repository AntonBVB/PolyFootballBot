from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from .clob import CLOBGateway
from .config import Settings
from .db import Database
from .models import EntryCandidate, OrderIntent, OrderKind, OrderSide, OrderStatus, PositionRecord, PositionStatus, TradeableOutcome, round_down
from .orderbook import extract_book_top

logger = logging.getLogger(__name__)


@dataclass
class EntryEngine:
    settings: Settings
    db: Database
    clob: CLOBGateway

    def scan(self, now: datetime | None = None) -> list[EntryCandidate]:
        now = now or datetime.now(timezone.utc)
        candidates: list[EntryCandidate] = []
        available = self.clob.available_usdc()
        if available < self.settings.min_available_usdc:
            logger.info("ENTRY_REJECTED reason=insufficient_balance available=%s", available)
            return candidates
        for outcome in self.db.list_tradeable_outcomes(dry_run=self.clob.dry_run):
            candidate = self._build_candidate(outcome, now)
            if candidate is None:
                continue
            candidates.append(candidate)
            self._place_entry(candidate)
        return candidates

    def _build_candidate(self, outcome: TradeableOutcome, now: datetime) -> EntryCandidate | None:
        if outcome.outcome_role.value == "DRAW":
            logger.info("OUTCOME_SKIPPED_DRAW market_id=%s outcome=%s", outcome.market_id, outcome.outcome_name)
            return None
        if not outcome.enable_orderbook:
            logger.info("MARKET_SKIPPED_NON_TRADEABLE market_id=%s reason=orderbook_disabled", outcome.market_id)
            return None
        if outcome.total_volume < self.settings.min_total_volume:
            return None
        if not (now < outcome.event_start_time <= now + timedelta(hours=self.settings.open_window_hours)):
            return None
        if self.db.has_open_order_or_position(outcome.market_id, outcome.tradable_token_id, dry_run=self.clob.dry_run):
            return None
        book = extract_book_top(self.clob.fetch_order_book(outcome.tradable_token_id))
        if book.best_ask is None or book.best_bid is None or book.spread is None:
            logger.info("BOOK_FETCH_FAILED token_id=%s reason=empty_book", outcome.tradable_token_id)
            return None
        # BUY NO entry uses the ask of the NO asset and later exits by selling the exact same NO asset.
        entry_price = round_down(book.best_ask, outcome.tick_size)
        if not (self.settings.entry_min <= entry_price <= self.settings.entry_max):
            return None
        if book.spread > self.settings.max_spread:
            return None
        shares = round_down(self.settings.buy_cost_usd / entry_price, 0.01)
        if shares <= 0:
            return None
        return EntryCandidate(outcome=outcome, book=book, entry_price=entry_price, shares=shares)

    def _place_entry(self, candidate: EntryCandidate) -> None:
        intent = OrderIntent(
            market_id=candidate.outcome.market_id,
            token_id=candidate.outcome.tradable_token_id,
            outcome_name=candidate.outcome.outcome_name,
            outcome_role=candidate.outcome.outcome_role,
            market_format=candidate.outcome.market_format,
            kind=OrderKind.ENTRY,
            side=OrderSide.BUY,
            price=candidate.entry_price,
            size=candidate.shares,
            dry_run=self.clob.dry_run,
        )
        result = self.clob.place_order(intent)
        self.db.record_order(intent, result)
        if result.status in {OrderStatus.OPEN, OrderStatus.FILLED} and result.filled_size > 0:
            self.db.open_position_from_fill(intent, result)
            logger.info("BUY_NO_ENTRY market_id=%s token_id=%s shares=%s price=%s", intent.market_id, intent.token_id, result.filled_size, intent.price)
        else:
            logger.info("ENTRY_REJECTED market_id=%s token_id=%s status=%s", intent.market_id, intent.token_id, result.status.value)


@dataclass
class ExitEngine:
    settings: Settings
    db: Database
    clob: CLOBGateway

    def monitor(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        for position in self.db.list_open_positions(dry_run=self.clob.dry_run):
            self._handle_position(position, now)

    def _handle_position(self, position: PositionRecord, now: datetime) -> None:
        if position.outcome_role.value == "DRAW":
            return
        book = extract_book_top(self.clob.fetch_order_book(position.token_id))
        if book.best_bid is None:
            self.db.mark_position_status(position.position_id or 0, PositionStatus.EXIT_PENDING, notes="Empty book during exit")
            return
        exit_kind = None
        if book.best_bid >= position.entry_price + self.settings.take_profit_delta:
            exit_kind = OrderKind.TP
        elif position.opened_at and now >= position.opened_at:
            # Protective exit uses the same outcome/token as the BUY NO entry whenever the prematch window has ended.
            exit_kind = OrderKind.PROTECTIVE_EXIT
        if exit_kind is None:
            return
        intent = OrderIntent(
            market_id=position.market_id,
            token_id=position.token_id,
            outcome_name=position.outcome_name,
            outcome_role=position.outcome_role,
            market_format=position.market_format,
            kind=exit_kind,
            side=OrderSide.SELL,
            price=round_down(book.best_bid, 0.01),
            size=position.shares,
            dry_run=self.clob.dry_run,
        )
        result = self.clob.place_order(intent)
        self.db.record_order(intent, result)
        if result.status in {OrderStatus.OPEN, OrderStatus.FILLED}:
            self.db.mark_position_status(position.position_id or 0, PositionStatus.CLOSED, notes=f"Closed via {exit_kind.value}")
            if exit_kind is OrderKind.TP:
                logger.info("TP_PLACED position_id=%s token_id=%s", position.position_id, position.token_id)
            else:
                logger.info("PROTECTIVE_EXIT_PLACED position_id=%s token_id=%s", position.position_id, position.token_id)
        else:
            if exit_kind is OrderKind.TP:
                logger.info("TP_REJECTED position_id=%s token_id=%s", position.position_id, position.token_id)
            else:
                logger.info("PROTECTIVE_EXIT_REJECTED position_id=%s token_id=%s", position.position_id, position.token_id)
