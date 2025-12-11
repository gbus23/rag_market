
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Set, Tuple

import pandas as pd  

from .config import NEWS_TOPIC
from .kafka_producer import create_producer, send_json
from .ticker_resolver_local import resolve_ticker_from_text
from . import scrapper


def row_to_event(row: pd.Series) -> dict:
    source = row["source"]
    title = row["title"]
    pub = row.get("published_at")

    published_at_iso: str | None
    if pd.isna(pub):
        published_at_iso = None
    else:
        if getattr(pub, "tzinfo", None) is None:
            pub_utc = pub.replace(tzinfo=timezone.utc)
        else:
            pub_utc = pub.astimezone(timezone.utc)
        published_at_iso = pub_utc.isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()

    ticker = resolve_ticker_from_text(title)
    tickers = [ticker] if ticker else []

    event_id = f"{source}:{title}"

    event = {
        "id": event_id,
        "source": source,
        "headline": title,
        "description": None,      
        "url": None,              
        "tickers": tickers,
        "published_at": published_at_iso,
        "received_at": now_iso,
        "raw": {
            "source": source,
            "title": title,
            "published_at_raw": str(pub),
        },
    }
    return event


def run_scraping_loop(
    interval_seconds: int = 60,
    fresh_minutes: int = 60,
    enable_bfm: bool = True,
    enable_ts: bool = True,
    enable_yahoo: bool = True,
    enable_zb: bool = True,
) -> None:
   

    producer = create_producer(client_id="web-scraper-ingestor")
    seen_keys: Set[Tuple[str, str]] = set()  # (source, title)

    print(
        f"[SCRAP] Starting web news ingestor -> topic '{NEWS_TOPIC}' "
        f"(interval={interval_seconds}s, fresh_minutes={fresh_minutes})"
    )

    while True:
        loop_start = time.perf_counter()

        
        df = scrapper.run_once(
            fresh_minutes=fresh_minutes,
            enable_bfm=enable_bfm,
            enable_ts=enable_ts,
            enable_yahoo=enable_yahoo,
            enable_zb=enable_zb,
        )

        if df is None or df.empty:
            print("[SCRAP] No headlines from scrapers.")
        else:
            new_count = 0
            for _, row in df.iterrows():
                key = (row["source"], row["title"])
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                event = row_to_event(row)
                send_json(producer, NEWS_TOPIC, event, key=event["id"])
                print(f"[SCRAP] Sent {event['id']} tickers={event['tickers']}")
                new_count += 1

            producer.flush()
            print(f"[SCRAP] Batch done, sent {new_count} new events.")

        elapsed = time.perf_counter() - loop_start
        to_sleep = max(0.0, interval_seconds - elapsed)
        print(f"[SCRAP] Sleeping {to_sleep:.1f}s...\n")
        time.sleep(to_sleep)


if __name__ == "__main__":
    run_scraping_loop(
        interval_seconds=60,
        fresh_minutes=1440,
        enable_bfm=False,
        enable_ts=True,
        enable_yahoo=True,
        enable_zb=True,
    )
