from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any, Protocol

from .models import ExchangeOrder, OrderIntent, OrderStatus

logger = logging.getLogger(__name__)


class SupportsOrderExchange(Protocol):
    def get_balance_allowance(self, params: Any) -> Any: ...
    def create_order(self, order_args: dict[str, Any]) -> dict[str, Any]: ...
    def post_order(self, signed_order: dict[str, Any], order_type: str = "GTC") -> dict[str, Any]: ...
    def get_order_book(self, token_id: str) -> dict[str, Any]: ...
    def get_order(self, order_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class BalanceAllowanceParams:
    asset_type: str
    signature_type: int
    funder: str | None = None


class CLOBClientError(RuntimeError):
    pass



def parse_available_balance(payload: Any) -> float:
    if isinstance(payload, dict):
        if "available" in payload:
            value = payload["available"]
        elif "balance" in payload:
            value = payload["balance"]
        elif isinstance(payload.get("data"), dict):
            return parse_available_balance(payload["data"])
        else:
            raise CLOBClientError("Allowance payload missing available/balance")
    else:
        value = payload

    number = float(value)
    if number > 1_000_000:
        return number / 1_000_000
    return number


@dataclass
class CLOBGateway:
    client: SupportsOrderExchange
    signature_type: int
    funder: str | None
    dry_run: bool

    def available_usdc(self) -> float:
        params = BalanceAllowanceParams(
            asset_type="COLLATERAL",
            signature_type=self.signature_type,
            funder=self.funder,
        )
        try:
            response = self.client.get_balance_allowance(params)
            return parse_available_balance(response)
        except Exception as exc:  # pragma: no cover - defensive against third-party client
            logger.exception("BALANCE_FETCH_FAILED error=%s", exc)
            raise CLOBClientError(str(exc)) from exc

    def fetch_order_book(self, token_id: str) -> dict[str, Any]:
        return self.client.get_order_book(token_id)

    def place_order(self, intent: OrderIntent) -> ExchangeOrder:
        if self.dry_run:
            logger.info(
                "DRY_RUN_ORDER_SIMULATED kind=%s side=%s token_id=%s price=%s size=%s",
                intent.kind.value,
                intent.side.value,
                intent.token_id,
                intent.price,
                intent.size,
            )
            return ExchangeOrder(
                order_id=f"dry-run:{intent.kind.value}:{intent.token_id}",
                status=OrderStatus.FILLED,
                filled_size=intent.size,
                payload={"simulated": True},
            )

        order_args = {
            "token_id": intent.token_id,
            "price": intent.price,
            "size": intent.size,
            "side": intent.side.value,
        }
        signed = self.client.create_order(order_args)
        payload = self.client.post_order(signed, order_type="GTC")
        status_raw = str(payload.get("status") or payload.get("order", {}).get("status") or "OPEN").upper()
        try:
            status = OrderStatus(status_raw)
        except ValueError:
            status = OrderStatus.UNKNOWN
        return ExchangeOrder(
            order_id=str(payload.get("orderID") or payload.get("id") or signed.get("id") or "unknown"),
            status=status,
            filled_size=float(payload.get("filledSize") or payload.get("filled_size") or 0.0),
            payload=json.loads(json.dumps(payload)),
            error_message=payload.get("errorMsg") or payload.get("error"),
        )

    def fetch_order_status(self, order_id: str) -> ExchangeOrder:
        payload = self.client.get_order(order_id)
        status_raw = str(payload.get("status") or "UNKNOWN").upper()
        try:
            status = OrderStatus(status_raw)
        except ValueError:
            status = OrderStatus.UNKNOWN
        return ExchangeOrder(
            order_id=order_id,
            status=status,
            filled_size=float(payload.get("filledSize") or payload.get("filled_size") or 0.0),
            payload=payload,
        )
