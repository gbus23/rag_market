# rag_news.py

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from threading import Thread, Lock
from typing import List, Dict, Optional

from kafka import KafkaConsumer

from ingestion.ticker_resolver_local import resolve_ticker_from_text


# =========================
# Configuration
# =========================

# Topic Kafka où arrivent les news normalisées
NEWS_TOPIC = os.getenv("NEWS_TOPIC", "news_raw")

# Bootstrap servers Kafka
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

# Taille max du buffer en RAM
NEWS_BUFFER_MAX_LEN = int(os.getenv("NEWS_BUFFER_MAX_LEN", "5000"))

# Âge max des news à prendre en compte (en heures)
NEWS_MAX_AGE_HOURS = float(os.getenv("NEWS_MAX_AGE_HOURS", "24"))


# =========================
# Buffer in-memory
# =========================

# Chaque élément est un dict représentant un message du topic news_raw
NEWS_BUFFER: deque[Dict] = deque(maxlen=NEWS_BUFFER_MAX_LEN)
NEWS_BUFFER_LOCK = Lock()


# =========================
# Consommation Kafka
# =========================

import time

def _consume_news_forever() -> None:
    consumer = KafkaConsumer(
        NEWS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        group_id=f"rag_news_buffer_{int(time.time())}",  # group unique à chaque run
        auto_offset_reset="earliest",
        enable_auto_commit=False,  # pas besoin de commit en dev
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    for msg in consumer:
        value = msg.value
        with NEWS_BUFFER_LOCK:
            NEWS_BUFFER.append(value)


def start_news_buffer_in_background() -> None:
    
    t = Thread(target=_consume_news_forever, daemon=True)
    t.start()


# =========================
# Helpers
# =========================

def _parse_iso(ts: str) -> datetime:
    """
    Parse une string ISO 8601 en datetime timezone-aware (UTC).
    """
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def _score_doc(doc: Dict, q_tokens: set[str], now: datetime) -> float:
    """
    Score simple = match lexical * poids de récence.
    - match lexical : nb de tokens de la query retrouvés dans (headline + description + source)
    - récence : 1 / (1 + âge_en_heures)
    """
    text_parts = [
        str(doc.get("headline", "")),
        str(doc.get("description", "")),
        str(doc.get("source", "")),
    ]
    text = " ".join(text_parts).lower()

    base = sum(1 for tok in q_tokens if tok in text)

    if base == 0:
        return 0.0

    published_str = doc.get("published_at") or doc.get("received_at")
    if published_str:
        pub_dt = _parse_iso(published_str)
    else:
        pub_dt = now

    age_hours = max((now - pub_dt).total_seconds() / 3600.0, 0.0)

    # Trop vieux → on rejette
    if age_hours > NEWS_MAX_AGE_HOURS:
        return 0.0

    recency_weight = 1.0 / (1.0 + age_hours)

    return base * recency_weight


def _doc_matches_ticker(doc: Dict, ticker: Optional[str]) -> bool:
    """
    Vérifie si un document correspond au ticker demandé.

    Logique :
    1) Si aucun ticker demandé → True
    2) Si doc["tickers"] contient déjà ce ticker → True
    3) Sinon, on infère via resolve_ticker_from_text(headline + description)
       en utilisant ton fichier d’alias + NAME_TO_TICKER.
    """
    if ticker is None:
        return True

    ticker_upper = ticker.upper()

    # 1) tickers renseignés par l’ingest (Finnhub / scrapper)
    doc_tickers = doc.get("tickers") or []
    doc_tickers_upper = {t.upper() for t in doc_tickers}
    if ticker_upper in doc_tickers_upper:
        return True

    # 2) fallback : inférence via le texte
    text = " ".join([
        str(doc.get("headline") or ""),
        str(doc.get("description") or ""),
    ])
    inferred = resolve_ticker_from_text(text)

    if inferred and inferred.upper() == ticker_upper:
        return True

    return False


# =========================
# API publique pour le RAG
# =========================

def retrieve_news_for_query(
    query: str,
    ticker: Optional[str] = None,
    max_results: int = 20,
) -> List[Dict]:
    """
    Lecture du buffer in-memory + filtre par ticker + scoring query.

    Args:
        query: question utilisateur (texte libre)
        ticker: ticker cible (ex: "TSLA") ou None
        max_results: nombre max de news retournées

    Returns:
        Liste de dicts:
        {
            "headline": str,
            "source": str,
            "published_at": str,
            "summary": str | None,
            "url": str | None,
            "tickers": List[str]
        }
    """
    if not query and not ticker:
        return []

    now = datetime.now(timezone.utc)

    # tokens simples de la query pour le match lexical
    q_tokens = {tok for tok in query.lower().split() if len(tok) > 2}

    # snapshot du buffer pour éviter de le locker trop longtemps
    with NEWS_BUFFER_LOCK:
        docs = list(NEWS_BUFFER)

    scored: List[tuple[float, Dict]] = []

    for doc in docs:
        # 1) filtre par ticker (avec fallback via resolver)
        if not _doc_matches_ticker(doc, ticker):
            continue

        # 2) scoring lexical + récence
        score = _score_doc(doc, q_tokens, now)

        # si on a une requête textuelle, mais aucun match lexical → skip
        if q_tokens and score == 0.0:
            continue

        # cas spécial : pas de query MAIS ticker demandé → on renvoie
        # quand même les news les plus récentes pour ce ticker
        if not q_tokens and ticker and score == 0.0:
            score = 0.1

        if score > 0.0:
            scored.append((score, doc))

    
    scored.sort(key=lambda x: x[0], reverse=True)

    
    top_docs = [d for _, d in scored[:max_results]]

    results: List[Dict] = []
    for d in top_docs:
        results.append(
            {
                "headline": d.get("headline"),
                "source": d.get("source"),
                "published_at": d.get("published_at") or d.get("received_at"),
                "summary": d.get("description") or d.get("raw", {}).get("summary"),
                "url": d.get("url") or d.get("raw", {}).get("url"),
                "tickers": d.get("tickers", []),
            }
        )

    return results


def get_buffer_stats() -> Dict[str, int]:
    """
    Petit helper de debug : permet de voir combien de docs sont en RAM.
    """
    with NEWS_BUFFER_LOCK:
        n = len(NEWS_BUFFER)
    return {"buffer_len": n, "buffer_max_len": NEWS_BUFFER_MAX_LEN}
