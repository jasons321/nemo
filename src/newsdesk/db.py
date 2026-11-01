"""SQLite storage. One table for raw articles, one for model scores.

Scores are keyed on (article, model, prompt_version), so changing the model or
prompt never overwrites earlier results and you can compare them later.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id           TEXT PRIMARY KEY,      -- sha1 of url
    ticker       TEXT NOT NULL,
    title        TEXT NOT NULL,
    url          TEXT NOT NULL,
    source       TEXT,
    published_at TEXT,                  -- ISO 8601, UTC
    fetched_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_ticker_time ON articles(ticker, published_at);

CREATE TABLE IF NOT EXISTS scores (
    article_id     TEXT NOT NULL REFERENCES articles(id),
    model          TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    relevance      REAL,
    sentiment      INTEGER,            -- -2..+2
    event_type     TEXT,
    confidence     REAL,
    reason         TEXT,
    scored_at      TEXT NOT NULL,
    PRIMARY KEY (article_id, model, prompt_version)
);
"""


def article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_articles(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert articles, skipping ones already stored. Returns number of new rows."""
    before = conn.total_changes
    conn.executemany(
        """INSERT OR IGNORE INTO articles
           (id, ticker, title, url, source, published_at, fetched_at)
           VALUES (:id, :ticker, :title, :url, :source, :published_at, :fetched_at)""",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def unscored(conn: sqlite3.Connection, model: str, prompt_version: str,
             ticker: str | None = None, limit: int | None = None) -> list[sqlite3.Row]:
    sql = """SELECT a.* FROM articles a
             LEFT JOIN scores s ON s.article_id = a.id
                  AND s.model = ? AND s.prompt_version = ?
             WHERE s.article_id IS NULL"""
    params: list = [model, prompt_version]
    if ticker:
        sql += " AND a.ticker = ?"
        params.append(ticker)
    sql += " ORDER BY a.published_at DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def save_score(conn: sqlite3.Connection, article_id: str, model: str,
               prompt_version: str, score: dict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO scores
           (article_id, model, prompt_version, relevance, sentiment,
            event_type, confidence, reason, scored_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (article_id, model, prompt_version, score["relevance"], score["sentiment"],
         score["event_type"], score["confidence"], score["reason"], now_iso()),
    )
    conn.commit()
