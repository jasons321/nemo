"""Command line entry point.

    newsdesk ingest            # fetch headlines for all tickers in config.yaml
    newsdesk score --limit 20  # score unscored headlines with the local LLM
    newsdesk show GOOGL        # print the latest scored headlines
"""
from __future__ import annotations

import argparse
import sys

from . import db
from .config import load_config
from .ingest import fetch_ticker
from .score import OllamaScorer


def cmd_ingest(cfg, args) -> None:
    conn = db.connect(cfg["db_path"])
    news = cfg.get("news", {})
    for ticker, info in cfg["tickers"].items():
        if args.ticker and ticker != args.ticker:
            continue
        try:
            rows = fetch_ticker(ticker, info["aliases"],
                                news.get("lookback_days", 7), news.get("max_per_ticker", 50))
        except RuntimeError as e:
            print(f"  {ticker}: {e}", file=sys.stderr)
            continue
        new = db.insert_articles(conn, rows)
        print(f"  {ticker}: {len(rows)} fetched, {new} new")


def cmd_score(cfg, args) -> None:
    conn = db.connect(cfg["db_path"])
    llm = cfg["llm"]
    scorer = OllamaScorer(llm["host"], llm["model"], llm.get("timeout_s", 120))
    scorer.check()

    todo = db.unscored(conn, llm["model"], llm["prompt_version"], args.ticker, args.limit)
    print(f"Scoring {len(todo)} headlines with {llm['model']} (prompt {llm['prompt_version']})")
    failures = 0
    for i, row in enumerate(todo, 1):
        company = cfg["tickers"][row["ticker"]]["name"]
        try:
            s = scorer.score(row["ticker"], company, row["title"])
        except Exception as e:  # keep going; one bad response shouldn't stop the batch
            failures += 1
            print(f"  [{i}] failed: {e}", file=sys.stderr)
            continue
        db.save_score(conn, row["id"], llm["model"], llm["prompt_version"], s.model_dump())
        print(f"  [{i}/{len(todo)}] {row['ticker']} {s.sentiment:+d} "
              f"{s.event_type:<16} {row['title'][:70]}")
    if failures:
        print(f"{failures} headline(s) failed to score; rerun to retry them.")


def cmd_show(cfg, args) -> None:
    conn = db.connect(cfg["db_path"])
    rows = conn.execute(
        """SELECT a.published_at, s.sentiment, s.relevance, s.event_type, a.title
           FROM articles a JOIN scores s ON s.article_id = a.id
           WHERE a.ticker = ? AND s.model = ? AND s.prompt_version = ?
           ORDER BY a.published_at DESC LIMIT ?""",
        (args.ticker, cfg["llm"]["model"], cfg["llm"]["prompt_version"], args.n),
    ).fetchall()
    for r in rows:
        print(f"{(r['published_at'] or '')[:16]}  {r['sentiment']:+d}  "
              f"rel={r['relevance']:.1f}  {r['event_type']:<16} {r['title'][:80]}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="newsdesk")
    p.add_argument("--config", default="config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest", help="fetch headlines")
    s.add_argument("--ticker")
    s = sub.add_parser("score", help="score unscored headlines with the local LLM")
    s.add_argument("--ticker")
    s.add_argument("--limit", type=int)
    s = sub.add_parser("show", help="print latest scored headlines for a ticker")
    s.add_argument("ticker")
    s.add_argument("-n", type=int, default=20)

    args = p.parse_args(argv)
    cfg = load_config(args.config)
    {"ingest": cmd_ingest, "score": cmd_score, "show": cmd_show}[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
