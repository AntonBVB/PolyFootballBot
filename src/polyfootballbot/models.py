from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Any


class AppMode(str, Enum):
    DRY_RUN = "dry-run"
    LIVE = "live"


class MarketType(str, Enum):
    BINARY_HOME_WIN = "BINARY_HOME_WIN"
    BINARY_AWAY_WIN = "BINARY_AWAY_WIN"
    BINARY_DRAW = "BINARY_DRAW"
    THREE_WAY_HOME = "THREE_WAY_HOME"
    THREE_WAY_DRAW = "THREE_WAY_DRAW"
    THREE_WAY_AWAY = "THREE_WAY_AWAY"
    OTHER = "OTHER"


class OutcomeRole(str, Enum):
    HOME = "HOME"
    DRAW = "DRAW"
    AWAY = "AWAY"
    OTHER = "OTHER"


class MarketFormat(str, Enum):
    BINARY = "BINARY"
    THREE_WAY = "THREE_WAY"
    OTHER = "OTHER"


class OrderKind(str, Enum):
    ENTRY = "ENTRY"
    TP = "TP"
    EXIT = "EXIT"
    PROTECTIVE_EXIT = "PROTECTIVE_EXIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    EXIT_PENDING = "EXIT_PENDING"


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    league_name: str
    home_team: str
    away_team: str
    start_time: datetime
    raw_json: str


@dataclass(frozen=True)
class MarketRecord:
    market_id: str
    event_id: str
    question: str
    slug: str
    market_type: MarketType
    market_format: MarketFormat
    total_volume: float
    tick_size: float
    neg_risk: bool
    enable_orderbook: bool
    active: bool
    closed: bool
    archived: bool
    live: bool
    raw_json: str


@dataclass(frozen=True)
class OutcomeRecord:
    outcome_id: str
    market_id: str
    outcome_name: str
    outcome_role: OutcomeRole
    token_id: str
    no_token_id: str | None
    is_tradeable: bool
    raw_json: str


@dataclass(frozen=True)
class DiscoveryBundle:
    event: EventRecord
    market: MarketRecord
    outcomes: tuple[OutcomeRecord, ...]


@dataclass(frozen=True)
class TradeableOutcome:
    market_id: str
    event_id: str
    event_start_time: datetime
    market_type: MarketType
    market_format: MarketFormat
    outcome_name: str
    outcome_role: OutcomeRole
    token_id: str
    no_token_id: str | None
    tick_size: float
    total_volume: float
    enable_orderbook: bool
    live: bool

    @property
    def tradable_token_id(self) -> str:
        # BUY NO / SELL NO must always use the same NO asset when available.
        return self.no_token_id or self.token_id


@dataclass(frozen=True)
class AssetBookTop:
    best_bid: float | None
    best_ask: float | None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round(self.best_ask - self.best_bid, 10)


@dataclass(frozen=True)
class OrderIntent:
    market_id: str
    token_id: str
    outcome_name: str
    outcome_role: OutcomeRole
    market_format: MarketFormat
    kind: OrderKind
    side: OrderSide
    price: float
    size: float
    dry_run: bool


@dataclass(frozen=True)
class ExchangeOrder:
    order_id: str
    status: OrderStatus
    filled_size: float
    payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(frozen=True)
class PositionRecord:
    position_id: int | None
    market_id: str
    token_id: str
    outcome_name: str
    outcome_role: OutcomeRole
    market_format: MarketFormat
    shares: float
    entry_price: float
    status: PositionStatus
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    live_detected_at: datetime | None = None
    notes: str | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class EntryCandidate:
    outcome: TradeableOutcome
    book: AssetBookTop
    entry_price: float
    shares: float


def round_down(value: float, step: float) -> float:
    quant = Decimal(str(step))
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_DOWN))
