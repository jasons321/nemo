# Roadmap

Assumes roughly 8 to 10 hours a week, starting Monday 2 November 2026.
Each module ends with something you can demo and a measured result you can put on a CV.
Christmas week is left as buffer.

| # | Module | Dates | Done when |
|---|--------|-------|-----------|
| 0 | Setup | 2 to 8 Nov | Ollama running, `ingest` and `score` work end to end, repo on GitHub |
| 1 | Sentiment dashboard | 9 to 22 Nov | 10 to 15 tickers, daily scheduled ingest, Streamlit deployed with a live link |
| 2 | Labelled set and evaluation | 23 Nov to 6 Dec | 300 hand-labelled headlines; FinBERT vs 2 to 3 local models compared |
| 3 | Event classifier | 7 to 13 Dec | Fine-tuned small transformer (or LoRA) vs prompted LLM, per-class precision/recall |
| 4 | Attention / hype tracker | 14 to 20 Dec | Reddit + news volume z-scores, spike flags, simple event study on volume and volatility |
| – | Buffer | 21 Dec to 3 Jan | Catch up, tidy code, write up modules 1 to 4 |
| 5 | RAG Q&A over filings | 4 to 17 Jan | 10-K chunks from EDGAR, cited answers, recall@k and faithfulness on 50+ questions |
| 6 | Daily briefing | 18 to 24 Jan | Cited per-ticker summary from deduplicated stories, factual-error rate checked |
| 7 | Polish and write-up | 25 to 31 Jan | README with results tables and charts, short demo video, CV bullets finalised |

## Module checklists

### 0. Setup (2 to 8 Nov)
- [ ] Install Ollama, pull a model that fits your hardware, run `newsdesk score --limit 5`
- [ ] Push to GitHub, add a licence and the not-financial-advice note
- [ ] Note your hardware and throughput (headlines/second) in the README

### 1. Sentiment dashboard (9 to 22 Nov)
- [ ] Expand `config.yaml` to 10 to 15 tickers with good aliases
- [ ] Add a second news source (Finnhub free tier) returning the same row shape
- [ ] Deduplicate syndicated stories (sentence embeddings + cosine threshold)
- [ ] Recency-weighted sentiment score per ticker
- [ ] Schedule `ingest` and `score` daily (cron or Task Scheduler)
- [ ] Overlay price (yfinance) on the sentiment chart
- [ ] Deploy to Streamlit Community Cloud
- **Milestone:** a live link you can put on your CV

### 2. Labelled set and evaluation (23 Nov to 6 Dec)
- [ ] Export 300 headlines to CSV, label sentiment, event type and relevance yourself
- [ ] Add a FinBERT baseline scorer with the same interface
- [ ] Compare 2 to 3 local models and zero-shot vs few-shot prompts
- [ ] Report F1, Cohen's kappa, run-to-run consistency and throughput
- [ ] Swap the placeholder few-shot examples in `score.py` for real ones from your set
- **Milestone:** results table in the README

### 3. Event classifier (7 to 13 Dec)
- [ ] Fine-tune a small transformer (e.g. DistilBERT/DeBERTa-small) on your event labels
- [ ] Optional: LoRA fine-tune a small LLM and compare
- [ ] Per-class precision/recall and a confusion matrix
- **Milestone:** "fine-tuned model vs prompted LLM" finding

### 4. Attention / hype tracker (14 to 20 Dec)
- [ ] Check current Reddit API terms; collect ticker mention counts
- [ ] Rolling z-score of mentions and news volume; flag spikes
- [ ] Event study: volume, volatility and returns after spikes vs matched non-spike days
- [ ] Watch for look-ahead bias in every step
- **Milestone:** one chart plus a short written finding

### 5. RAG Q&A over filings (4 to 17 Jan)
- [ ] Pull 10-Ks/10-Qs from EDGAR (proper User-Agent, respect rate limits)
- [ ] Chunk by section, embed locally, store in Chroma or sqlite-vec
- [ ] Answer with citations, and say "not found" when unsupported
- [ ] Write 50 to 100 questions with known answers, including unanswerable ones
- [ ] Measure recall@k, citation accuracy, faithfulness and refusal accuracy
- **Milestone:** Q&A box in the dashboard plus evaluation table

### 6. Daily briefing (18 to 24 Jan)
- [ ] Retrieve the day's top deduplicated stories per ticker
- [ ] Generate a short cited briefing with the local LLM
- [ ] Hand-check 30 briefings for factual errors and unsupported claims
- **Milestone:** briefing panel on the ticker page

### 7. Polish and write-up (25 to 31 Jan)
- [ ] Architecture diagram and results tables in the README
- [ ] 2-minute demo video or GIF
- [ ] Final CV bullets and talking points for interviews

## If time runs short
Ship modules 0 to 4 plus a thin RAG over 10-Ks only. That is still a strong project.
