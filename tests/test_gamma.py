from datetime import datetime, timedelta, timezone

from polyfootballbot.gamma import normalize_market
from polyfootballbot.models import OutcomeRole


def test_normalize_market_accepts_string_outcomes() -> None:
    payload = {
        "id": "m-three-way-1",
        "question": "Team A vs Team B",
        "slug": "team-a-vs-team-b",
        "volume": 25000,
        "minimum_tick_size": 0.01,
        "enableOrderBook": True,
        "clobTokenIds": '["tok-home","tok-draw","tok-away"]',
        "outcomes": ["Team A", "Draw", "Team B"],
        "event": {
            "id": "e-three-way-1",
            "homeTeam": "Team A",
            "awayTeam": "Team B",
            "startDate": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "seriesSlug": "soccer",
        },
    }

    bundle = normalize_market(payload)
    assert bundle is not None
    assert len(bundle.outcomes) == 3

    assert bundle.outcomes[0].outcome_role == OutcomeRole.HOME
    assert bundle.outcomes[0].is_tradeable is True

    assert bundle.outcomes[1].outcome_role == OutcomeRole.DRAW
    assert bundle.outcomes[1].is_tradeable is False

    assert bundle.outcomes[2].outcome_role == OutcomeRole.AWAY
    assert bundle.outcomes[2].is_tradeable is True
