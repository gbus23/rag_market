from __future__ import annotations

import json
from typing import Any, Dict, Optional

from confluent_kafka import Producer, KafkaError

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


def send_json(producer: Producer, topic: str, payload: Dict[str, Any], key: Optional[str] = None) -> None:
    def delivery_report(err, msg):
        if err is not None:
            print(f"[KAFKA] Delivery failed for record {msg.value()}: {err}")
        else:
            pass

    producer.produce(
        topic=topic,
        key=str(key) if key is not None else None,
        value=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        on_delivery=delivery_report,
    )
    producer.poll(0)
