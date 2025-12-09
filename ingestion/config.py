from __future__ import annotations

import os
from dotenv import load_dotenv

# Load variables from .env at project root
load_dotenv()

KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

NEWS_TOPIC: str = os.getenv("NEWS_TOPIC", "news_raw")
PRICES_TOPIC: str = os.getenv("PRICES_TOPIC", "prices_raw")

FINNHUB_API_KEY: str | None = os.getenv("FINNHUB_API_KEY")
MARKETAUX_API_KEY: str | None = os.getenv("MARKETAUX_API_KEY")
ALPHAVANTAGE_API_KEY: str | None = os.getenv("ALPHAVANTAGE_API_KEY")
OPENFIGI_API_KEY: str | None = os.getenv("OPENFIGI_API_KEY")
