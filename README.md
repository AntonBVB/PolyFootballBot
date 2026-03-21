# PolyFootballBot

Production-ready Polymarket CLOB football bot focused strictly on **prematch match-result markets** with a single lifecycle:

- **Entry:** BUY the **NO** token for a team outcome.
- **Exit:** SELL the **same NO** token.
- **Draw:** always forbidden.

The implementation intentionally skips any market or outcome that introduces ambiguity. It is safer to miss a trade than to create inconsistent sqlite state.

## What the bot trades

Allowed universe:

- Binary home-win markets.
- Binary away-win markets.
- 3-way match-result markets with `HOME / DRAW / AWAY` outcomes.

Forbidden universe:

- Binary draw markets.
- Draw outcome in 3-way markets.
- Over/Under.
- BTTS.
- Spread / handicap.
- Props or any non-match-result market.

## Core architecture

- `gamma.py` fetches and normalizes Gamma discovery payloads.
- `market_classifier.py` classifies markets and outcomes, and hard-rejects draw/non-match-result paths.
- `clob.py` wraps balance allowance parsing, orderbook fetches, and order placement.
- `strategy.py` contains the BUY NO entry engine and SELL same-NO-token exit engine.
- `reconcile.py` syncs local OPEN orders with exchange state.
- `db.py` persists events, markets, outcomes, orders, and positions in sqlite.
- `scheduler.py` runs isolated background loops so one failing task does not kill the bot.

## Why draw is forbidden

Draw is excluded everywhere:

- never becomes a candidate;
- never becomes a signal;
- never opens a position;
- never participates in take-profit;
- never participates in protective exit.

This is enforced both during market discovery and during position handling.

## Configuration

Copy the example file and fill in live credentials only when you are ready to trade real funds.

```bash
cp .env.example .env
```

### Important variables

- `APP_MODE=dry-run|live`
- `PRIVATE_KEY`, `FUNDER`, `SIGNATURE_TYPE=2`
- `ENTRY_MIN=0.73`
- `ENTRY_MAX=0.83`
- `TAKE_PROFIT_DELTA=0.05`
- `MAX_SPREAD=0.03`
- `MIN_TOTAL_VOLUME=20000`
- `BUY_COST_USD=5`
- `MIN_AVAILABLE_USDC=6`
- `OPEN_WINDOW_HOURS=12`
- `FAST_MODE_BEFORE_START_MINUTES=3`
- `PREMATCH_POLL_SECONDS=60`
- `FAST_POLL_SECONDS=15`
- `DISCOVERY_SECONDS=3600`
- `RECONCILE_SECONDS=600`

Invalid live configuration fails fast on startup instead of silently degrading.

## Local run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python -m polyfootballbot
```

## Dry-run mode

Dry-run executes the full pipeline without sending real orders:

- discovery still stores normalized markets/outcomes;
- balance checks still run;
- entry/exit decisions still run;
- the app uses the built-in `NullExchangeClient` simulation only in dry-run;
- simulated orders are logged as `DRY_RUN_ORDER_SIMULATED`;
- dry-run records never block live trading because sqlite queries are always mode-aware.

```bash
APP_MODE=dry-run PYTHONPATH=src python -m polyfootballbot
```

## Live mode

Live mode requires a valid funded wallet configuration. In `APP_MODE=live` the bot now builds a real authenticated `py_clob_client.ClobClient`, derives API credentials with `create_or_derive_api_creds()`, and fails loudly if client initialization does not succeed.

```bash
APP_MODE=live \
PRIVATE_KEY=0x... \
FUNDER=0x... \
PYTHONPATH=src python -m polyfootballbot
```

In live mode the bot validates credentials at startup and preserves exchange payloads for orders in sqlite. If you previously ran an older fake-live build that produced `sim-*` order ids or simulated balances, clear those stale records from sqlite before enabling real live trading so they cannot contaminate operator expectations.

## Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f bot
```

## BUY NO / SELL NO lifecycle

1. Discovery stores only supported football match-result markets.
2. Entry scan checks each tradeable `HOME` or `AWAY` outcome.
3. The bot fetches the orderbook for the exact NO asset that will be traded.
4. Entry price uses the **best ask** of that NO asset.
5. Position size is `round_down(BUY_COST_USD / entry_price, 0.01)`.
6. Exit uses the **same token_id** via SELL.
7. Take-profit triggers when `best_bid >= entry_price + TAKE_PROFIT_DELTA`.
8. Protective exit uses the same token if the position must be closed defensively.

## Reconcile

`reconcile.py` periodically checks local OPEN orders against exchange state.

Goals:

- update stale OPEN orders;
- capture fills/cancels/rejections;
- prevent old local state from blocking valid new entries;
- keep dry-run and live state separated.

## Checking sqlite state

```bash
sqlite3 data/polyfootballbot.db '.tables'
sqlite3 data/polyfootballbot.db 'select market_id, outcome_name, outcome_role, token_id, no_token_id from outcomes limit 10;'
sqlite3 data/polyfootballbot.db 'select order_id, kind, side, status, dry_run from orders order by created_at desc limit 20;'
sqlite3 data/polyfootballbot.db 'select position_id, token_id, outcome_name, status, dry_run from positions order by position_id desc limit 20;'
```

## Tests

```bash
export PYTHONPATH=src
pytest -q
```

The tests cover:

- market classification;
- outcome tradeability;
- best bid / best ask extraction;
- allowance parsing;
- dry-run isolation;
- BUY NO -> SELL same NO lifecycle.
