"""News ingestion from Google News RSS (no API key needed).

Only headlines, URLs and metadata are stored, not article bodies, which keeps
you on the safe side of publishers' terms. Add Finnhub/NewsAPI later as extra
sources that return the same dict shape.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser

from .db import article_id, now_iso

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-GB&gl=GB&ceid=GB:en"
USER_AGENT = "newsdesk/0.1 (personal research project)"


def build_query(aliases: list[str], lookback_days: int) -> str:
    names = " OR ".join(f'"{a}"' for a in aliases)
    return f"({names}) stock when:{lookback_days}d"


def feed_url(aliases: list[str], lookback_days: int) -> str:
    return GOOGLE_NEWS_RSS.format(q=quote_plus(build_query(aliases, lookback_days)))


def _clean_title(title: str, source: str | None) -> str:
    # Google News appends " - Source Name" to every title.
    if source and title.endswith(f" - {source}"):
        return title[: -len(source) - 3].strip()
    return title.strip()


def parse_feed(raw_or_url: str | bytes, ticker: str, limit: int = 50) -> list[dict]:
    """Turn an RSS document (or URL) into article rows."""
    feed = feedparser.parse(raw_or_url, agent=USER_AGENT)
    if feed.get("bozo") and not feed.entries:
        raise RuntimeError(f"Could not read feed for {ticker}: {feed.get('bozo_exception')}")

    rows, fetched = [], now_iso()
    for entry in feed.entries[:limit]:
        url = entry.get("link")
        if not url:
            continue
        source = entry.get("source", {}).get("title")
        published = None
        if entry.get("published_parsed"):
            ts = calendar.timegm(entry.published_parsed)
            published = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
        rows.append({
            "id": article_id(url),
            "ticker": ticker,
            "title": _clean_title(entry.get("title", ""), source),
            "url": url,
            "source": source,
            "published_at": published,
            "fetched_at": fetched,
        })
    return rows


def fetch_ticker(ticker: str, aliases: list[str], lookback_days: int = 7,
                 limit: int = 50) -> list[dict]:
    return parse_feed(feed_url(aliases, lookback_days), ticker, limit)
