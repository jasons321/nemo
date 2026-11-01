"""Streamlit dashboard: `streamlit run app.py`"""
import sqlite3

import pandas as pd
import streamlit as st

from newsdesk.config import load_config

cfg = load_config()
st.set_page_config(page_title="newsdesk", layout="wide")
st.title("newsdesk")
st.caption("Research tool, not financial advice.")

ticker = st.sidebar.selectbox("Ticker", list(cfg["tickers"]))
min_rel = st.sidebar.slider("Minimum relevance", 0.0, 1.0, 0.5, 0.1)

conn = sqlite3.connect(cfg["db_path"])
df = pd.read_sql_query(
    """SELECT a.published_at, a.source, a.title, a.url,
              s.sentiment, s.relevance, s.event_type, s.confidence, s.reason
       FROM articles a JOIN scores s ON s.article_id = a.id
       WHERE a.ticker = ? AND s.model = ? AND s.prompt_version = ?""",
    conn,
    params=(ticker, cfg["llm"]["model"], cfg["llm"]["prompt_version"]),
)

if df.empty:
    st.info("No scored headlines yet. Run `newsdesk ingest` then `newsdesk score`.")
    st.stop()

df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
df = df[df["relevance"] >= min_rel]

c1, c2, c3 = st.columns(3)
c1.metric("Headlines", len(df))
c2.metric("Mean sentiment", f"{df['sentiment'].mean():+.2f}")
c3.metric("Most common event", df["event_type"].mode().iat[0] if len(df) else "-")

st.subheader("Daily sentiment")
daily = (df.set_index("published_at").resample("D")["sentiment"]
           .agg(["mean", "count"]).rename(columns={"mean": "sentiment", "count": "headlines"}))
st.line_chart(daily["sentiment"])
st.bar_chart(daily["headlines"])

st.subheader("Headlines")
st.dataframe(
    df.sort_values("published_at", ascending=False)[
        ["published_at", "sentiment", "event_type", "relevance", "title", "source", "reason", "url"]
    ],
    column_config={"url": st.column_config.LinkColumn("link")},
    hide_index=True,
    use_container_width=True,
)
