PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    league_name TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    start_time TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS markets (
    market_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    slug TEXT NOT NULL,
    market_type TEXT NOT NULL,
    market_format TEXT NOT NULL,
    total_volume REAL NOT NULL,
    tick_size REAL NOT NULL,
    neg_risk INTEGER NOT NULL DEFAULT 0,
    enable_orderbook INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    closed INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    live INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id TEXT PRIMARY KEY,
    market_id TEXT NOT NULL REFERENCES markets(market_id) ON DELETE CASCADE,
    outcome_name TEXT NOT NULL,
    outcome_role TEXT NOT NULL,
    token_id TEXT NOT NULL,
    no_token_id TEXT,
    is_tradeable INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (market_id, token_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    market_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    outcome_name TEXT NOT NULL,
    outcome_role TEXT NOT NULL,
    market_format TEXT NOT NULL,
    kind TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    size REAL NOT NULL,
    filled_size REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exchange_payload_json TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_market_token_status_mode
ON orders (market_id, token_id, status, dry_run);

CREATE TABLE IF NOT EXISTS positions (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    outcome_name TEXT NOT NULL,
    outcome_role TEXT NOT NULL,
    market_format TEXT NOT NULL,
    shares REAL NOT NULL,
    entry_price REAL NOT NULL,
    status TEXT NOT NULL,
    opened_at TEXT,
    closed_at TEXT,
    live_detected_at TEXT,
    notes TEXT,
    dry_run INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_positions_market_token_status_mode
ON positions (market_id, token_id, status, dry_run);
