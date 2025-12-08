from __future__ import annotations
import time
import requests
from datetime import datetime, timezone
from typing import Set, Dict, Any, List

from .config import FINNHUB_API_KEY, NEWS_TOPIC
from .kafka_producer import create_producer, send_json

BASE_URL = "https://finnhub.io/api/v1/news"

def fetch_news(category: str = "general") -> List[Dict[str, Any]]:
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY is not set in .env")
    params = {
        "category": category,
        "token": FINNHUB_API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []

def normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    art_id = str(article.get("id") or article.get("url"))

    # timestamp
    dt_epoch = article.get("datetime")
    if isinstance(dt_epoch, (int, float)):
        published_at = datetime.fromtimestamp(dt_epoch, tz=timezone.utc).isoformat()
    else:
        published_at = now_iso

    related = article.get("related") or ""
    tickers = [t.strip() for t in related.split(",") if t.strip()]

    return {
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

def run_polling(interval_seconds: int = 60, category: str = "general") -> None:
    producer = create_producer(client_id="finnhub-news-ingestor")
    seen_ids: Set[str] = set()

    print(f"[FINNHUB] Starting news ingestor -> topic '{NEWS_TOPIC}', category={category}")

    while True:
        try:
            print("[FINNHUB] Fetching news...")
            articles = fetch_news(category=category)

            if not articles:
                print("[FINNHUB] No articles.")
            else:
                articles_sorted = sorted(articles, key=lambda a: a.get("datetime") or 0)
                for art in articles_sorted:
                    normalized = normalize_article(art)
                    art_id = normalized["id"]
                    if art_id in seen_ids:
                        continue
                    seen_ids.add(art_id)
                    send_json(producer, NEWS_TOPIC, normalized, key=art_id)
                    print(f"[FINNHUB] Sent article {art_id} tickers={normalized['tickers']}")
                producer.flush()
        except Exception as e:
            print(f"[FINNHUB] Error: {e}")

        print(f"[FINNHUB] Sleeping {interval_seconds} seconds...")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_polling(interval_seconds=60, category="general")
