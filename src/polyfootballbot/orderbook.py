from __future__ import annotations

from typing import Any

from .models import AssetBookTop


class EmptyOrderBookError(RuntimeError):
    pass



def extract_book_top(book_payload: dict[str, Any]) -> AssetBookTop:
    bids = book_payload.get("bids") or []
    asks = book_payload.get("asks") or []
    best_bid = max((float(level["price"] if isinstance(level, dict) else level[0]) for level in bids), default=None)
    best_ask = min((float(level["price"] if isinstance(level, dict) else level[0]) for level in asks), default=None)
    return AssetBookTop(best_bid=best_bid, best_ask=best_ask)
