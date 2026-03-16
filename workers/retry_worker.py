"""
Retry Worker — Nexora Customer Success Digital FTE.

Consumes messages from the dead-letter topic, applies exponential
back-off, and re-publishes them to their original inbound topic for
another processing attempt.  After MAX_REPUBLISH_ATTEMPTS the message
is archived to the dead-letter topic with a FINAL_FAILURE marker and
an alert is logged.

Run with:
    python -m workers.retry_worker

Environment variables:
    KAFKA_BOOTSTRAP_SERVERS      default: localhost:9092
    RETRY_CONSUMER_GROUP         default: nexora-retry-workers
    RETRY_MAX_ATTEMPTS           default: 3
    RETRY_BASE_BACKOFF_S         default: 5
    LOG_LEVEL                    default: INFO
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.streaming.kafka_consumer import NexoraConsumer
from backend.streaming.kafka_producer import NexoraProducer
from backend.streaming.topics import KafkaTopic

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("workers.retry_worker")

MAX_REPUBLISH_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
BASE_BACKOFF_S: float = float(os.getenv("RETRY_BASE_BACKOFF_S", "5"))

# Map original topic names back to KafkaTopic objects
_TOPIC_BY_NAME: dict[str, Any] = {
    str(t): t for t in KafkaTopic.ALL_TOPICS
}


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def handle_dead_letter(payload: dict) -> None:
    """
    Process one dead-letter message.

    Decision logic:
      - Extract original_topic and retry_count from payload
      - If retry_count < MAX_REPUBLISH_ATTEMPTS: re-publish with back-off
      - Else: log FINAL_FAILURE and archive (leave in dead-letter committed)
    """
    meta = payload.get("_meta", {})
    event_id = meta.get("event_id", "unknown")
    original_topic_name = payload.get("original_topic", "")
    original_payload = payload.get("original_payload", {})
    failure_reason = payload.get("failure_reason", "unknown")

    # Extract retry count from original payload's _meta
    orig_meta = original_payload.get("_meta", {})
    retry_count = orig_meta.get("retry_count", 0)

    logger.info(
        "Dead-letter received | event_id=%s | original_topic=%s | retry=%d | reason=%s",
        event_id, original_topic_name, retry_count, failure_reason,
    )

    if retry_count >= MAX_REPUBLISH_ATTEMPTS:
        logger.error(
            "FINAL_FAILURE | event_id=%s | original_topic=%s | reason=%s | "
            "Manual review required.",
            event_id, original_topic_name, failure_reason,
        )
        _alert_on_call(event_id, original_topic_name, failure_reason)
        return  # commit and discard — message is permanently failed

    # Exponential back-off before re-publishing
    backoff = BASE_BACKOFF_S * (2 ** retry_count)
    logger.info(
        "Re-publishing after %.1fs back-off | event_id=%s | attempt=%d/%d",
        backoff, event_id, retry_count + 1, MAX_REPUBLISH_ATTEMPTS,
    )
    time.sleep(backoff)

    # Increment retry counter in the payload
    updated_payload = {
        **original_payload,
        "_meta": {**orig_meta, "retry_count": retry_count + 1},
    }

    # Look up the original topic object
    original_topic = _TOPIC_BY_NAME.get(original_topic_name)
    if original_topic is None:
        logger.error(
            "Cannot re-publish: unknown original topic %r | event_id=%s",
            original_topic_name, event_id,
        )
        return

    producer = NexoraProducer()
    customer_id = updated_payload.get("customer_id")
    producer.publish(
        topic=original_topic,
        payload=updated_payload,
        key=customer_id,
    )
    producer.flush(timeout=10.0)

    logger.info(
        "Re-published | event_id=%s → %s | retry_count=%d",
        event_id, original_topic_name, retry_count + 1,
    )


def _alert_on_call(event_id: str, topic: str, reason: str) -> None:
    """
    Placeholder for on-call alerting integration.

    In production, replace with:
      - PagerDuty API call
      - Slack webhook
      - Email via SES
    """
    logger.critical(
        "ON-CALL ALERT | event_id=%s | topic=%s | reason=%s | "
        "TODO: integrate PagerDuty/Slack here.",
        event_id, topic, reason,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logger.info("=== Nexora Retry Worker Starting ===")

    group_id = os.getenv("RETRY_CONSUMER_GROUP", "nexora-retry-workers")
    consumer = NexoraConsumer(
        topics=[KafkaTopic.DEAD_LETTER],
        group_id=group_id,
        auto_offset_reset="earliest",
    )

    logger.info("Listening on dead-letter topic | group=%s", group_id)
    consumer.run(handler=handle_dead_letter)
    logger.info("=== Retry Worker Stopped ===")


if __name__ == "__main__":
    main()
