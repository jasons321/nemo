import json

import pytest

from newsdesk import db
from newsdesk.ingest import build_query, parse_feed
from newsdesk.score import HeadlineScore, build_messages, parse_response

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>t</title>
<item>
  <title>Alphabet beats on cloud revenue - Reuters</title>
  <link>https://example.com/a</link>
  <pubDate>Fri, 30 Oct 2026 14:00:00 GMT</pubDate>
  <source url="https://reuters.com">Reuters</source>
</item>
<item>
  <title>Google faces new antitrust probe - BBC</title>
  <link>https://example.com/b</link>
  <pubDate>Sat, 31 Oct 2026 09:30:00 GMT</pubDate>
  <source url="https://bbc.co.uk">BBC</source>
</item>
</channel></rss>"""


def test_parse_feed_strips_source_suffix_and_parses_dates():
    rows = parse_feed(SAMPLE_RSS, "GOOGL")
    assert [r["title"] for r in rows] == [
        "Alphabet beats on cloud revenue", "Google faces new antitrust probe"]
    assert rows[0]["published_at"] == "2026-10-30T14:00:00+00:00"
    assert rows[0]["source"] == "Reuters"


def test_build_query():
    assert build_query(["Alphabet", "Google"], 7) == '("Alphabet" OR "Google") stock when:7d'


def test_insert_is_idempotent_and_unscored_tracks_model(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    rows = parse_feed(SAMPLE_RSS, "GOOGL")
    assert db.insert_articles(conn, rows) == 2
    assert db.insert_articles(conn, rows) == 0  # duplicates ignored

    assert len(db.unscored(conn, "m1", "v1")) == 2
    score = {"relevance": 1, "sentiment": 1, "event_type": "earnings",
             "confidence": 0.8, "reason": "x"}
    db.save_score(conn, rows[0]["id"], "m1", "v1", score)
    assert len(db.unscored(conn, "m1", "v1")) == 1
    assert len(db.unscored(conn, "m1", "v2")) == 2  # new prompt version rescores everything


def test_parse_response_valid_and_rule_enforced():
    s = parse_response(json.dumps({"relevance": 0.1, "sentiment": 2, "event_type": "other",
                                   "confidence": 0.5, "reason": "passing mention"}))
    assert s.sentiment == 0  # low relevance forces neutral


def test_parse_response_rejects_out_of_range():
    with pytest.raises(Exception):
        parse_response(json.dumps({"relevance": 1, "sentiment": 5, "event_type": "earnings",
                                   "confidence": 0.5, "reason": "x"}))


def test_few_shot_examples_match_schema():
    msgs = build_messages("GOOGL", "Alphabet", "test")
    for m in msgs:
        if m["role"] == "assistant":
            HeadlineScore.model_validate_json(m["content"])
    assert msgs[-1]["content"].endswith("Headline: test")
