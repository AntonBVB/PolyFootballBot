# PolyFootballBot

Initial project skeleton for a production-ready Polymarket CLOB football bot.

## Scope of this initial skeleton

- Python 3.11+ `src/` layout
- Docker and docker compose setup
- Environment-based configuration with startup validation
- Logging setup
- SQLite auto-init schema
- Scheduler skeleton (no trading logic)
- Smoke tests with pytest

> This stage intentionally **does not** include any trading logic.

## Project structure

```text
.
├── db/
│   └── schema.sql
├── src/
│   └── polyfootballbot/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── db.py
│       ├── logging_setup.py
│       └── scheduler.py
├── tests/
│   ├── test_app_smoke.py
│   └── test_config.py
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Quick start (local)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=src
python -m polyfootballbot
```

## Quick start (docker)

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f bot
```

## Testing

```bash
export PYTHONPATH=src
pytest -q
```
