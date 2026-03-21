from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from typing import Any

import httpx

from .market_classifier import classify_market_type, classify_outcome_role, is_tradeable_outcome, market_format_from_type
from .models import DiscoveryBundle, EventRecord, MarketRecord, MarketType, OutcomeRecord, OutcomeRole

logger = logging.getLogger(__name__)


class GammaError(RuntimeError):
    pass


def _outcome_name_from_payload(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or "").strip()
    return str(item).strip()


@dataclass
class GammaClient:
    base_url: str
    timeout_seconds: float = 10.0

    def fetch_soccer_markets(self) -> list[dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/markets"
        params = {"tag_slug": "soccer", "limit": 500, "active": "true"}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("DISCOVERY_FAILED gamma_request_error=%s", exc)
            raise GammaError(str(exc)) from exc
        payload = response.json()
        if not isinstance(payload, list):
            raise GammaError("Gamma response must be a list of markets")
        return payload



def parse_clob_token_ids(raw_token_ids: Any) -> list[str]:
    if raw_token_ids is None:
        return []
    if isinstance(raw_token_ids, str):
        value = raw_token_ids.strip()
        if not value:
            return []
        loaded = json.loads(value)
        if not isinstance(loaded, list):
            raise GammaError("clobTokenIds JSON string must decode to a list")
        return [str(item) for item in loaded]
    if isinstance(raw_token_ids, list):
        return [str(item) for item in raw_token_ids]
    raise GammaError("Unsupported clobTokenIds format")



def _parse_start_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)



def normalize_market(payload: dict[str, Any]) -> DiscoveryBundle | None:
    event = payload.get("event") or {}
    home_team = str(event.get("homeTeam") or payload.get("homeTeam") or "").strip()
    away_team = str(event.get("awayTeam") or payload.get("awayTeam") or "").strip()
    outcomes = payload.get("outcomes") or []
    outcome_names = [_outcome_name_from_payload(item) for item in outcomes]
    market_type = classify_market_type(str(payload.get("question", "")), outcome_names)
    if market_type == MarketType.OTHER:
        return None
    if market_type == MarketType.BINARY_HOME_WIN:
        normalized_question = str(payload.get("question", "")).lower()
        if away_team and normalized_question.startswith(f"will {away_team.lower()}"):
            market_type = MarketType.BINARY_AWAY_WIN
    if market_type == MarketType.THREE_WAY_HOME:
        # Home/draw/away are encoded outcome-by-outcome below.
        pass

    event_id = str(event.get("id") or payload.get("eventId") or payload.get("slug") or payload.get("id"))
    event_record = EventRecord(
        event_id=event_id,
        league_name=str(event.get("seriesSlug") or event.get("league") or payload.get("category") or "soccer"),
        home_team=home_team,
        away_team=away_team,
        start_time=_parse_start_time(str(event.get("startDate") or payload.get("endDate") or payload.get("startDate"))),
        raw_json=json.dumps(event or payload, sort_keys=True),
    )

    market_id = str(payload.get("id"))
    market_record = MarketRecord(
        market_id=market_id,
        event_id=event_id,
        question=str(payload.get("question", "")),
        slug=str(payload.get("slug", market_id)),
        market_type=market_type,
        market_format=market_format_from_type(market_type),
        total_volume=float(payload.get("volume") or payload.get("liquidity") or 0.0),
        tick_size=float(payload.get("minimum_tick_size") or payload.get("tickSize") or 0.01),
        neg_risk=bool(payload.get("negRisk", False)),
        enable_orderbook=bool(payload.get("enableOrderBook", payload.get("enable_orderbook", False))),
        active=bool(payload.get("active", True)),
        closed=bool(payload.get("closed", False)),
        archived=bool(payload.get("archived", False)),
        live=bool(payload.get("live", False)),
        raw_json=json.dumps(payload, sort_keys=True),
    )

    token_ids = parse_clob_token_ids(payload.get("clobTokenIds"))
    outcome_records: list[OutcomeRecord] = []
    for index, outcome in enumerate(outcomes):
        if isinstance(outcome, dict):
            outcome_name = str(outcome.get("name", "")).strip()
            token_id = str(outcome.get("clobTokenId") or outcome.get("token_id") or token_ids[index] if index < len(token_ids) else "")
            no_token_id = outcome.get("noTokenId")
        else:
            outcome_name = str(outcome).strip()
            token_id = token_ids[index] if index < len(token_ids) else ""
            no_token_id = None
        if not token_id:
            continue
        role = classify_outcome_role(outcome_name, home_team, away_team)
        outcome_market_type = market_type
        if market_type == MarketType.THREE_WAY_HOME:
            if role == OutcomeRole.HOME:
                outcome_market_type = MarketType.THREE_WAY_HOME
            elif role == OutcomeRole.AWAY:
                outcome_market_type = MarketType.THREE_WAY_AWAY
            elif role == OutcomeRole.DRAW:
                outcome_market_type = MarketType.THREE_WAY_DRAW
        outcome_records.append(
            OutcomeRecord(
                outcome_id=f"{market_id}:{index}:{role.value}",
                market_id=market_id,
                outcome_name=outcome_name,
                outcome_role=role,
                token_id=token_id,
                no_token_id=str(no_token_id) if no_token_id is not None else None,
                is_tradeable=is_tradeable_outcome(outcome_market_type, role),
                raw_json=json.dumps(outcome if isinstance(outcome, dict) else {"name": outcome_name}, sort_keys=True),
            )
        )

    return DiscoveryBundle(event=event_record, market=market_record, outcomes=tuple(outcome_records))
