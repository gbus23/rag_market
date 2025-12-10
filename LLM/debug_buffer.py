from __future__ import annotations

import time
from datetime import datetime, timezone

from LLM.rag_news import (
    NEWS_BUFFER,
    NEWS_BUFFER_LOCK,
    NEWS_MAX_AGE_HOURS,
    start_news_buffer_in_background,
)


def _parse_iso(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.now(timezone.utc)


def debug_buffer(ticker_filter: str = "TSLA", max_docs: int = 200):
    ticker_filter = ticker_filter.upper()

    with NEWS_BUFFER_LOCK:
        docs = list(NEWS_BUFFER)

    print("\n=== DEBUG BUFFER (MATCHING TICKER ONLY) ===")
    print(f"Total docs in buffer : {len(docs)}")
    print(f"Ticker filter        : {ticker_filter}")
    print(f"NEWS_MAX_AGE_HOURS   : {NEWS_MAX_AGE_HOURS}")
    print("Showing only docs where ticker is present in `tickers`.\n")

    now = datetime.now(timezone.utc)
    shown = 0

    for idx, doc in enumerate(docs):
        doc_tickers = {t.upper() for t in (doc.get("tickers") or [])}

        # On ne garde QUE ceux qui contiennent le ticker demandé
        if ticker_filter not in doc_tickers:
            continue

        published = doc.get("published_at") or doc.get("received_at")
        if published:
            dt = _parse_iso(published)
            age_hours = (now - dt).total_seconds() / 3600.0
        else:
            age_hours = None

        print(f"[{idx:03}] MATCH")
        print(f"      headline   : {doc.get('headline')}")
        print(f"      source     : {doc.get('source')}")
        print(f"      published  : {published}")
        print(f"      tickers    : {sorted(doc_tickers)}")
        if age_hours is not None:
            print(f"      age_hours  : {age_hours:.2f}")
        else:
            print("      age_hours  : ?")
        print("-" * 100)

        shown += 1
        if shown >= max_docs:
            break

    if shown == 0:
        print(f"No documents in buffer contain ticker {ticker_filter}.")


if __name__ == "__main__":
    start_news_buffer_in_background()
    print("Waiting a bit to fill the buffer...")
    time.sleep(5)
    debug_buffer("NVDA")
