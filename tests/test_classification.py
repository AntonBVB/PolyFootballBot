from polyfootballbot.market_classifier import classify_market_type, classify_outcome_role, is_tradeable_match_result_market, is_tradeable_outcome
from polyfootballbot.models import MarketType, OutcomeRole


def test_binary_market_classification() -> None:
    assert classify_market_type("Will ACF Fiorentina win on 2026-03-16?", ["Yes", "No"]) == MarketType.BINARY_HOME_WIN
    assert classify_market_type("Will US Cremonese win on 2026-03-16?", ["Yes", "No"]) == MarketType.BINARY_HOME_WIN
    assert classify_market_type("Will US Cremonese vs. ACF Fiorentina end in a draw?", ["Yes", "No"]) == MarketType.BINARY_DRAW


def test_non_match_result_market_classification() -> None:
    assert classify_market_type("US Cremonese vs. ACF Fiorentina: O/U 2.5", ["Over", "Under"]) == MarketType.OTHER
    assert classify_market_type("US Cremonese vs. ACF Fiorentina: Both Teams to Score", ["Yes", "No"]) == MarketType.OTHER
    assert classify_market_type("Spread: ACF Fiorentina (-1.5)", ["Yes", "No"]) == MarketType.OTHER


def test_three_way_outcomes_are_tradeable_except_draw() -> None:
    assert classify_outcome_role("Team A", "Team A", "Team B") == OutcomeRole.HOME
    assert classify_outcome_role("Draw", "Team A", "Team B") == OutcomeRole.DRAW
    assert classify_outcome_role("Team B", "Team A", "Team B") == OutcomeRole.AWAY
    assert is_tradeable_outcome(MarketType.THREE_WAY_HOME, OutcomeRole.HOME) is True
    assert is_tradeable_outcome(MarketType.THREE_WAY_AWAY, OutcomeRole.AWAY) is True
    assert is_tradeable_outcome(MarketType.THREE_WAY_DRAW, OutcomeRole.DRAW) is False


def test_tradeable_match_result_filter() -> None:
    assert is_tradeable_match_result_market("Will ACF Fiorentina win on 2026-03-16?", ["Yes", "No"]) is True
    assert is_tradeable_match_result_market("US Cremonese vs. ACF Fiorentina: Both Teams to Score", ["Yes", "No"]) is False


from polyfootballbot.gamma import normalize_market


def test_normalize_market_supports_string_outcomes() -> None:
    payload = {
        "id": "m-string-outcomes",
        "question": "Alpha FC vs Beta FC",
        "slug": "alpha-vs-beta",
        "volume": 25000,
        "minimum_tick_size": 0.01,
        "enableOrderBook": True,
        "clobTokenIds": ["home-token", "draw-token", "away-token"],
        "outcomes": ["Alpha FC", "Draw", "Beta FC"],
        "event": {
            "id": "event-1",
            "homeTeam": "Alpha FC",
            "awayTeam": "Beta FC",
            "startDate": "2026-03-21T15:00:00Z",
            "seriesSlug": "soccer",
        },
    }

    bundle = normalize_market(payload)

    assert bundle is not None
    assert [outcome.outcome_name for outcome in bundle.outcomes] == ["Alpha FC", "Draw", "Beta FC"]
    assert [outcome.is_tradeable for outcome in bundle.outcomes] == [True, False, True]
