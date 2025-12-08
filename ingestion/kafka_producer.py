from __future__ import annotations

import json
from typing import Any, Dict, Optional

from confluent_kafka import Producer

from .config import KAFKA_BOOTSTRAP_SERVERS


def create_producer(client_id: str = "ingestor") -> Producer:
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "client.id": client_id,
    }
    return Producer(conf)


def _delivery_report(err, msg) -> None:
    if err is not None:
        print(f"[KAFKA] Delivery failed for record {msg.key()}: {err}")


def send_json(
    producer: Producer,
    topic: str,
    value: Dict[str, Any],
    key: Optional[str] = None,
) -> None:
    payload = json.dumps(value).encode("utf-8")
    producer.produce(
        topic=topic,
        key=key.encode("utf-8") if key else None,
        value=payload,
        callback=_delivery_report,
    )
    producer.poll(0)
