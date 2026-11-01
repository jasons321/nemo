# newsdesk

A local-LLM research tool for retail traders: pulls financial news headlines,
scores them for relevance, sentiment and event type with an open-weight model
running on your own machine, and shows the results per ticker.

> Research and information tool only. Not financial advice.

See [ROADMAP.md](ROADMAP.md) for the planned modules (event classifier,
hype tracker, RAG over filings, daily briefings).

## Quick start

1. **Install Ollama** from https://ollama.com and pull a small model:
   ```bash
   ollama pull qwen2.5:3b     # or any small instruct model that fits your hardware
   ```
   Set the same model name under `llm.model` in `config.yaml`.

2. **Install the project** (Python 3.10+):
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Run it:**
   ```bash
   newsdesk ingest                # fetch headlines for tickers in config.yaml
   newsdesk score --limit 20      # score them with the local LLM
   newsdesk show GOOGL            # print results
   streamlit run app.py           # open the dashboard
   ```

4. **Tests:** `pytest`

## How it works

```
Google News RSS ──> ingest.py ──> SQLite (articles)
                                     │
                       score.py (Ollama, JSON-schema output)
                                     │
                              SQLite (scores) ──> app.py (Streamlit)
```

- **Storage:** `data/newsdesk.db`. Scores are keyed on article, model and
  prompt version, so changing either never overwrites old results and you can
  compare them.
- **Scoring:** each headline gets `relevance` (0 to 1), `sentiment` (-2 to +2,
  from a shareholder's view), `event_type`, `confidence` and a one-line
  `reason`. Ollama's schema-constrained decoding keeps small models from
  returning broken JSON.
- **Changing the prompt:** edit `SYSTEM_PROMPT` / `FEW_SHOT` in
  `src/newsdesk/score.py` and bump `llm.prompt_version` in `config.yaml`.

## Project layout

```
config.yaml            tickers, model and paths
app.py                 Streamlit dashboard
src/newsdesk/
  config.py            config loading
  db.py                SQLite schema and helpers
  ingest.py            news fetching (Google News RSS)
  score.py             local LLM scoring
  cli.py               `newsdesk` command
tests/                 offline tests (no network or LLM needed)
```

## Notes

- Only headlines, URLs and metadata are stored, not article text.
  Don't commit `data/` to GitHub.
- When you backtest anything, remember the model may have seen historical
  market reactions in training. Prefer news from after its training cutoff.
