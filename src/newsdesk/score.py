"""Headline scoring with a local LLM via Ollama.

Uses Ollama's schema-constrained output (`format=<JSON schema>`) so small models
can't return broken JSON, then validates the result with pydantic.
"""
from __future__ import annotations

import json
from typing import Literal

import requests
from pydantic import BaseModel, Field

EventType = Literal[
    "earnings", "guidance", "product", "legal_regulatory", "m_and_a",
    "analyst_rating", "management", "macro", "other",
]


class HeadlineScore(BaseModel):
    relevance: float = Field(ge=0, le=1, description="How much the headline is about this company")
    sentiment: int = Field(ge=-2, le=2, description="Likely impact for a shareholder")
    event_type: EventType
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(max_length=300)


SYSTEM_PROMPT = """You are a financial news analyst. Score one headline for a specific company,
from the perspective of someone who holds its shares.

Sentiment scale:
 +2 clearly material good news (big earnings beat, major contract, favourable ruling)
 +1 mildly positive
  0 neutral, mixed, or not about the company
 -1 mildly negative
 -2 clearly material bad news (big miss, major fine, guidance cut, key exec exit)

Relevance: 1.0 if the company is the main subject, around 0.5 if it is one of several,
near 0 if it is only mentioned in passing or not at all.
If relevance is below 0.3, sentiment must be 0.

Keep the reason to one short sentence. Reply with JSON only."""

# Few-shot examples help small models a lot. Replace these with real ones from
# your own labelled set once you have it.
FEW_SHOT = [
    ("GOOGL", "Alphabet",
     "Alphabet shares jump as cloud revenue beats estimates",
     {"relevance": 1.0, "sentiment": 2, "event_type": "earnings", "confidence": 0.9,
      "reason": "Earnings beat in a key growth segment."}),
    ("GOOGL", "Alphabet",
     "EU fines Google over adtech practices",
     {"relevance": 1.0, "sentiment": -1, "event_type": "legal_regulatory", "confidence": 0.7,
      "reason": "Regulatory fine; impact depends on size versus expectations."}),
    ("MSFT", "Microsoft",
     "Five tech stocks to watch this week, including Microsoft and Apple",
     {"relevance": 0.2, "sentiment": 0, "event_type": "other", "confidence": 0.8,
      "reason": "Listicle mention with no company-specific news."}),
]


def _user_msg(ticker: str, company: str, headline: str) -> str:
    return f"Company: {company} ({ticker})\nHeadline: {headline}"


def build_messages(ticker: str, company: str, headline: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for t, c, h, out in FEW_SHOT:
        msgs.append({"role": "user", "content": _user_msg(t, c, h)})
        msgs.append({"role": "assistant", "content": json.dumps(out)})
    msgs.append({"role": "user", "content": _user_msg(ticker, company, headline)})
    return msgs


def parse_response(content: str) -> HeadlineScore:
    score = HeadlineScore.model_validate_json(content)
    if score.relevance < 0.3 and score.sentiment != 0:
        score.sentiment = 0  # enforce the rubric rule even if the model ignores it
    return score


class OllamaScorer:
    def __init__(self, host: str, model: str, timeout_s: int = 120):
        self.url = host.rstrip("/") + "/api/chat"
        self.model = model
        self.timeout_s = timeout_s

    def score(self, ticker: str, company: str, headline: str) -> HeadlineScore:
        resp = requests.post(
            self.url,
            json={
                "model": self.model,
                "messages": build_messages(ticker, company, headline),
                "format": HeadlineScore.model_json_schema(),
                "stream": False,
                "options": {"temperature": 0, "seed": 42},
            },
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return parse_response(resp.json()["message"]["content"])

    def check(self) -> None:
        """Fail early with a helpful message if Ollama isn't running or the model is missing."""
        base = self.url.rsplit("/api/", 1)[0]
        try:
            tags = requests.get(base + "/api/tags", timeout=5).json()
        except requests.RequestException as e:
            raise RuntimeError(f"Ollama isn't reachable at {base}. Is `ollama serve` running?") from e
        names = {m["name"] for m in tags.get("models", [])}
        if self.model not in names and f"{self.model}:latest" not in names:
            raise RuntimeError(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
