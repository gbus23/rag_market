# ingestion/ingest_news_scraping.py
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Set, Tuple

import pandas as pd  # pour gérer les Timestamp / NaT

from .config import NEWS_TOPIC
from .kafka_producer import create_producer, send_json
from .ticker_resolver_local import resolve_ticker_from_text

# On importe ton script de scraping comme un module
from . import scrapping


def row_to_event(row: pd.Series) -> dict:
    """Convertit une ligne du DataFrame scrapping -> event normalisé pour Kafka."""
    source = row["source"]
    title = row["title"]
    pub = row.get("published_at")

    # published_at -> ISO UTC
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

    # Résolution du ticker à partir du titre
    ticker = resolve_ticker_from_text(title)
    tickers = [ticker] if ticker else []

    # ID simple : combinaison source + titre
    event_id = f"{source}:{title}"

    event = {
        "id": event_id,
        "source": source,
        "headline": title,
        "description": None,      # on n’a pas encore de corps d’article
        "url": None,              # ton scraper ne les stocke pas encore
        "tickers": tickers,
        "published_at": published_at_iso,
        "received_at": now_iso,
        "raw": {
            "source": source,
            "title": title,
            # On peut ajouter la date brute pour debug
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
    """
    Boucle infinie :
    - scrape les sources (via scrapping.run_once)
    - filtre les nouveaux titres (seen_keys)
    - envoie dans Kafka (topic NEWS_TOPIC)
    """

    producer = create_producer(client_id="web-scraper-ingestor")
    seen_keys: Set[Tuple[str, str]] = set()  # (source, title)

    print(
        f"[SCRAP] Starting web news ingestor -> topic '{NEWS_TOPIC}' "
        f"(interval={interval_seconds}s, fresh_minutes={fresh_minutes})"
    )

    while True:
        loop_start = time.perf_counter()

        # On réutilise ta fonction run_once comme "lib"
        df = scrapping.run_once(
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

        # Respecter l’intervalle de polling
        elapsed = time.perf_counter() - loop_start
        to_sleep = max(0.0, interval_seconds - elapsed)
        print(f"[SCRAP] Sleeping {to_sleep:.1f}s...\n")
        time.sleep(to_sleep)


if __name__ == "__main__":
    # Version simple : toutes les sources activées, interval et fenetre par défaut
    run_scraping_loop(
        interval_seconds=60,
        fresh_minutes=60,
        enable_bfm=True,
        enable_ts=True,
        enable_yahoo=True,
        enable_zb=True,
    )
