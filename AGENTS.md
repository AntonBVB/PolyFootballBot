# AGENTS.md

## Goal
Build a production-ready Polymarket CLOB football bot from scratch.

## Hard rules
- Entry is BUY NO only.
- Exit is SELL the same NO token only.
- Draw is always forbidden.
- Do not trade draw.
- Do not use draw in entry.
- Do not use draw in exit.
- Do not use draw in hedge.
- Only match-result markets are allowed.
- Over/Under, BTTS, Spread, props, and any non-match-result markets are forbidden.
- Better skip a trade than create inconsistent sqlite state.
- Dry-run and live state must not block each other.

## Technical rules
- Python 3.11+
- Docker
- docker compose
- sqlite
- py_clob_client
- requests or httpx
- typing
- logging
- pydantic and/or dataclasses
- pytest

## Quality rules
- Build from scratch
- No legacy SELL-entry logic
- Modular code
- Outcome-level uniqueness
- Reconcile task required
- best_bid = max(bids)
- best_ask = min(asks)
- Add comments in critical places only
- Add tests for critical logic

## Workflow
- Make small reviewable changes
- Keep README updated
- Add tests whenever critical logic is added
- Prefer safety over aggressiveness
