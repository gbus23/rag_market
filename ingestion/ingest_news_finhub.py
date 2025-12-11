from __future__ import annotations
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Set, Dict, Any, List
from .ticker_resolver_local import resolve_ticker_from_text
from .config import FINNHUB_API_KEY, NEWS_TOPIC
from .kafka_producer import create_producer, send_json

BASE_URL = "https://finnhub.io/api/v1/news"


def fetch_news(
    category: str = "general",
    window_minutes: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch latest news from Finnhub and keep only articles
    whose datetime is within the last `window_minutes`.
    """
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY is not set in .env")

    params = {
        "category": category,
        "token": FINNHUB_API_KEY,
    }

    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list):
        return []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)

    filtered: List[Dict[str, Any]] = []
    for art in data:
        dt_epoch = art.get("datetime")
        if isinstance(dt_epoch, (int, float)):
            published = datetime.fromtimestamp(dt_epoch, tz=timezone.utc)
        else:
            # si pas de datetime, on skip (pour éviter d'injecter du bruit)
            continue

        if published >= cutoff:
            filtered.append(art)

    print(
        f"[FINNHUB] Fetched {len(data)} articles, "
        f"kept {len(filtered)} newer than {cutoff.isoformat()} "
        f"(window={window_minutes} min)"
    )
    return filtered


def normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    art_id = str(article.get("id") or article.get("url"))

    # timestamp conversion
    dt_epoch = article.get("datetime")
    if isinstance(dt_epoch, (int, float)):
        published_at = datetime.fromtimestamp(dt_epoch, tz=timezone.utc).isoformat()
    else:
        published_at = now_iso

    # 1) Try Finnhub related tickers first (if exists)
    related = article.get("related") or ""
    tickers = [t.strip().upper() for t in related.split(",") if t.strip()]

    # 2) If none found, use text-based resolver
    if not tickers:
        text = (article.get("headline") or "") + " " + (article.get("summary") or "")
        detected = resolve_ticker_from_text(text)
        if detected:
            tickers = [detected]

    return{
        "id": art_id,
        "source": "Finnhub",
        "headline": article.get("headline"),
        "description": article.get("summary"),
        "url": article.get("url"),
        "tickers": tickers,
        "published_at": published_at,
        "received_at": now_iso,
        "raw": article,
    }

def run_polling(
    interval_seconds: int = 60,
    category: str = "general",
    window_minutes: int = 30,
) -> None:
    """
    Poll Finnhub every `interval_seconds`, but only send articles
    that are less than `window_minutes` old.
    """
    producer = create_producer(client_id="finnhub-news-ingestor")
    seen_ids: Set[str] = set()

    print(
        f"[FINNHUB] Starting news ingestor -> topic '{NEWS_TOPIC}', "
        f"category={category}, window={window_minutes} min"
    )

    while True:
        try:
            print("[FINNHUB] Fetching news...")
            articles = fetch_news(category=category, window_minutes=window_minutes)

            if not articles:
                print("[FINNHUB] No recent articles in the time window.")
            else:
                articles_sorted = sorted(articles, key=lambda a: a.get("datetime") or 0)

                for art in articles_sorted:
                    normalized = normalize_article(art)
                    art_id = normalized["id"]

                    if art_id in seen_ids:
                        continue
                    seen_ids.add(art_id)

                    send_json(producer, NEWS_TOPIC, normalized, key=art_id)
                    print(
                        f"[FINNHUB] Sent article {art_id} "
                        f"published_at={normalized['published_at']} "
                        f"tickers={normalized['tickers']}"
                    )

                producer.flush()
        except Exception as e:
            print(f"[FINNHUB] Error: {e}")

        print(f"[FINNHUB] Sleeping {interval_seconds} seconds...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    # fenêtre de 30 minutes, polling toutes les 60 secondes
    run_polling(interval_seconds=60, category="general", window_minutes=1440)
