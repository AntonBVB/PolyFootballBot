from __future__ import annotations

from .models import MarketFormat, MarketType, OutcomeRole


_FORBIDDEN_PATTERNS = (
    "o/u",
    "over/under",
    "both teams to score",
    "btts",
    "spread",
    "handicap",
    "player",
    "shots",
    "corners",
    "cards",
    "props",
)


def classify_market_type(question: str, outcomes: list[str] | tuple[str, ...]) -> MarketType:
    normalized = question.strip().lower()
    if any(pattern in normalized for pattern in _FORBIDDEN_PATTERNS):
        return MarketType.OTHER

    normalized_outcomes = [outcome.strip().lower() for outcome in outcomes]
    if len(normalized_outcomes) == 3 and "draw" in normalized_outcomes:
        draw_index = normalized_outcomes.index("draw")
        if draw_index == 1:
            return MarketType.THREE_WAY_HOME
        return MarketType.OTHER

    if "draw" in normalized and "end in a draw" in normalized:
        return MarketType.BINARY_DRAW

    if normalized.startswith("will ") and normalized.endswith("?") and " win on " in normalized:
        return MarketType.BINARY_HOME_WIN

    return MarketType.OTHER



def market_format_from_type(market_type: MarketType) -> MarketFormat:
    if market_type in {MarketType.BINARY_HOME_WIN, MarketType.BINARY_AWAY_WIN, MarketType.BINARY_DRAW}:
        return MarketFormat.BINARY
    if market_type in {MarketType.THREE_WAY_HOME, MarketType.THREE_WAY_AWAY, MarketType.THREE_WAY_DRAW}:
        return MarketFormat.THREE_WAY
    return MarketFormat.OTHER



def classify_outcome_role(outcome_name: str, home_team: str, away_team: str) -> OutcomeRole:
    normalized = outcome_name.strip().lower()
    if normalized == "draw":
        return OutcomeRole.DRAW
    if normalized == home_team.strip().lower():
        return OutcomeRole.HOME
    if normalized == away_team.strip().lower():
        return OutcomeRole.AWAY
    return OutcomeRole.OTHER



def is_tradeable_outcome(market_type: MarketType, outcome_role: OutcomeRole) -> bool:
    if outcome_role == OutcomeRole.DRAW:
        return False
    if outcome_role not in {OutcomeRole.HOME, OutcomeRole.AWAY}:
        return False
    return market_type in {
        MarketType.BINARY_HOME_WIN,
        MarketType.BINARY_AWAY_WIN,
        MarketType.THREE_WAY_HOME,
        MarketType.THREE_WAY_AWAY,
    }



def is_tradeable_match_result_market(question: str, outcomes: list[str] | tuple[str, ...]) -> bool:
    market_type = classify_market_type(question, outcomes)
    return market_type in {
        MarketType.BINARY_HOME_WIN,
        MarketType.BINARY_AWAY_WIN,
        MarketType.THREE_WAY_HOME,
    }
