"""
Kafka Producer — Nexora Customer Success Digital FTE.

Wraps confluent-kafka's Producer with:
  - JSON serialisation
  - delivery confirmation callbacks
  - structured logging
  - graceful shutdown (flush on exit)

Usage::

    from backend.streaming.kafka_producer import NexoraProducer
    from backend.streaming.topics import KafkaTopic

    producer = NexoraProducer()

    producer.publish(
        topic=KafkaTopic.GMAIL_INCOMING,
        key="CUST-001",
        payload={
            "customer_id": "CUST-001",
            "channel": "email",
            "content": "I cannot find my invoice.",
            "from_email": "sarah@example.com",
            "from_name": "Sarah Chen",
        },
    )
"""

from __future__ import annotations

import json
import logging
import os
import socket
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Runtime import guard — confluent-kafka is optional in development
# ---------------------------------------------------------------------------

try:
    from confluent_kafka import Producer, KafkaError  # type: ignore[import]
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False
    logger.warning(
        "confluent-kafka not installed. NexoraProducer will run in DRY-RUN mode "
        "(messages logged but not sent). Install: pip install confluent-kafka"
    )


# ---------------------------------------------------------------------------
# Producer
# ---------------------------------------------------------------------------


class NexoraProducer:
    """
    Thread-safe Kafka producer for the Nexora CS agent.

    In development (no Kafka / no confluent-kafka), the producer runs in
    DRY-RUN mode and logs every message instead of sending it.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> None:
        self._bootstrap = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._client_id = client_id or f"nexora-producer-{socket.gethostname()}"
        self._dry_run = not _KAFKA_AVAILABLE
        self._producer = self._build_producer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(
        self,
        topic: Any,           # KafkaTopic._Topic or plain str
        payload: dict,
        key: Optional[str] = None,
        on_delivery: Optional[Callable] = None,
    ) -> str:
        """
        Publish a JSON payload to a Kafka topic.

        Automatically injects:
          - event_id   — UUIDv4 for tracing
          - produced_at — UTC ISO-8601 timestamp
          - producer_id — this instance's client_id

        Args:
            topic: KafkaTopic._Topic or topic name string.
            payload: Dict to serialise as JSON.
            key: Optional Kafka partition key (e.g. customer_id).
            on_delivery: Optional callback(err, msg) invoked on ack/nack.

        Returns:
            event_id string for downstream correlation.
        """
        topic_name = str(topic)
        event_id = str(uuid4())

        enriched = {
            **payload,
            "_meta": {
                "event_id": event_id,
                "produced_at": datetime.now(timezone.utc).isoformat(),
                "producer_id": self._client_id,
                "topic": topic_name,
            },
        }

        encoded_value = json.dumps(enriched, ensure_ascii=False, default=str).encode("utf-8")
        encoded_key = key.encode("utf-8") if key else None

        if self._dry_run:
            logger.info(
                "[DRY-RUN] PUBLISH → %s | key=%s | event_id=%s | payload=%s",
                topic_name, key, event_id, json.dumps(payload)[:200],
            )
            return event_id

        try:
            self._producer.produce(
                topic=topic_name,
                key=encoded_key,
                value=encoded_value,
                callback=on_delivery or self._default_delivery_callback,
            )
            self._producer.poll(0)  # trigger callbacks without blocking
            logger.debug("Queued → %s | key=%s | event_id=%s", topic_name, key, event_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to publish to %s: %s", topic_name, exc)
            raise

        return event_id

    def publish_inbound(
        self,
        channel: str,
        customer_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Convenience wrapper: publish a normalised inbound message to the
        channel-appropriate topic.

        Args:
            channel: "email" | "whatsapp" | "web_form"
            customer_id: External customer identifier.
            content: Raw message text.
            metadata: Any extra channel-specific fields.

        Returns:
            event_id
        """
        from backend.streaming.topics import KafkaTopic  # noqa: PLC0415

        topic = KafkaTopic.by_channel(channel)
        payload = {
            "customer_id": customer_id,
            "channel": channel,
            "content": content,
            **(metadata or {}),
        }
        return self.publish(topic=topic, payload=payload, key=customer_id)

    def publish_response(
        self,
        customer_id: str,
        channel: str,
        response_text: str,
        ticket_ref: Optional[str] = None,
        escalated: bool = False,
    ) -> str:
        """Publish an agent response to the agent_responses topic."""
        from backend.streaming.topics import KafkaTopic  # noqa: PLC0415

        payload = {
            "customer_id": customer_id,
            "channel": channel,
            "response": response_text,
            "ticket_ref": ticket_ref,
            "escalated": escalated,
        }
        return self.publish(
            topic=KafkaTopic.AGENT_RESPONSES,
            payload=payload,
            key=customer_id,
        )

    def publish_escalation(
        self,
        customer_id: str,
        ticket_ref: str,
        reason: str,
        severity: str,
        channel: str,
        customer_name: str,
    ) -> str:
        """Publish an escalation event to the escalations topic."""
        from backend.streaming.topics import KafkaTopic  # noqa: PLC0415

        payload = {
            "customer_id": customer_id,
            "ticket_ref": ticket_ref,
            "reason": reason,
            "severity": severity,
            "channel": channel,
            "customer_name": customer_name,
        }
        return self.publish(
            topic=KafkaTopic.ESCALATIONS,
            payload=payload,
            key=customer_id,
        )

    def flush(self, timeout: float = 10.0) -> None:
        """Block until all queued messages are delivered (or timeout)."""
        if not self._dry_run and self._producer:
            remaining = self._producer.flush(timeout=timeout)
            if remaining > 0:
                logger.warning("%d messages were NOT delivered before flush timeout.", remaining)

    def __enter__(self) -> "NexoraProducer":
        return self

    def __exit__(self, *_: Any) -> None:
        self.flush()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_producer(self) -> Any:
        if self._dry_run:
            return None

        conf = {
            "bootstrap.servers": self._bootstrap,
            "client.id": self._client_id,
            "acks": "all",                 # wait for all in-sync replica acks
            "retries": 5,
            "retry.backoff.ms": 500,
            "compression.type": "snappy",  # reduce network bandwidth
            "linger.ms": 5,                # small batching window
            "batch.size": 65536,
        }
        return Producer(conf)

    @staticmethod
    def _default_delivery_callback(err: Any, msg: Any) -> None:
        if err:
            logger.error(
                "Delivery FAILED | topic=%s | key=%s | error=%s",
                msg.topic(), msg.key(), err,
            )
        else:
            logger.debug(
                "Delivered | topic=%s | partition=%d | offset=%d",
                msg.topic(), msg.partition(), msg.offset(),
            )
