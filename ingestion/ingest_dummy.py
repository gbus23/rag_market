from __future__ import annotations

import time
from datetime import datetime, timezone

from .config import NEWS_TOPIC
from .kafka_producer import create_producer, send_json


def run_dummy(interval_seconds: int = 5) -> None:
    producer = create_producer(client_id="dummy-ingestor")
    i = 0

    print(f"[DUMMY] Starting dummy ingestor -> topic '{NEWS_TOPIC}'")

    while True:
        i += 1
        now = datetime.now(timezone.utc).isoformat()

        msg = {
            "id": f"dummy-{i}",
            "source": "dummy",
            "headline": f"Dummy news #{i}",
            "description": "This is a fake news item used to test the pipeline.",
            "url": "https://example.com",
            "tickers": ["TSLA"],
            "published_at": now,
            "received_at": now,
        }

        send_json(producer, NEWS_TOPIC, msg, key=msg["id"])
        print(f"[DUMMY] Sent message {msg['id']}")

        producer.flush()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_dummy()
