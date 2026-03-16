"""
Kafka Consumer — Nexora Customer Success Digital FTE.

Wraps confluent-kafka's Consumer with:
  - JSON deserialisation
  - at-least-once delivery semantics (manual commit after processing)
  - configurable error handling
  - graceful shutdown via stop() or SIGINT/SIGTERM

Usage::

    from backend.streaming.kafka_consumer import NexoraConsumer
    from backend.streaming.topics import KafkaTopic

    def handle_message(payload: dict) -> None:
        print(payload["customer_id"], payload["content"])

    consumer = NexoraConsumer(
        topics=[KafkaTopic.GMAIL_INCOMING],
        group_id="api-workers",
    )
    consumer.run(handler=handle_message)   # blocks; Ctrl-C to stop
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)

try:
    from confluent_kafka import Consumer, KafkaError, KafkaException  # type: ignore[import]
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False
    logger.warning(
        "confluent-kafka not installed. NexoraConsumer cannot consume messages. "
        "Install: pip install confluent-kafka"
    )


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------


class NexoraConsumer:
    """
    Kafka consumer that delivers decoded JSON payloads to a handler function.

    Commit strategy: manual commit **after** the handler returns successfully.
    On handler exception the message is NOT committed so it will be redelivered.
    After MAX_RETRIES failures the raw payload is sent to the dead-letter topic.
    """

    MAX_RETRIES: int = 3
    POLL_TIMEOUT_S: float = 1.0

    def __init__(
        self,
        topics: List[Any],            # list of KafkaTopic._Topic or str
        group_id: str,
        bootstrap_servers: Optional[str] = None,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self._topic_names = [str(t) for t in topics]
        self._group_id = group_id
        self._bootstrap = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._auto_offset_reset = auto_offset_reset
        self._running = False
        self._consumer = self._build_consumer()

        # Register OS signal handlers for graceful shutdown
        signal.signal(signal.SIGINT,  self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, handler: Callable[[dict], None]) -> None:
        """
        Start the consume loop. Blocks until stop() is called or a signal received.

        Args:
            handler: Callable receiving the decoded JSON payload dict.
                     Must raise on failure so the message is not committed.
        """
        if not _KAFKA_AVAILABLE:
            logger.error("confluent-kafka not available — consumer cannot start.")
            return

        self._running = True
        self._consumer.subscribe(self._topic_names)
        logger.info(
            "Consumer started | group=%s | topics=%s",
            self._group_id, self._topic_names,
        )

        try:
            while self._running:
                msg = self._consumer.poll(timeout=self.POLL_TIMEOUT_S)

                if msg is None:
                    continue  # poll timeout — normal

                if msg.error():
                    self._handle_error(msg.error())
                    continue

                self._dispatch(msg, handler)

        except KafkaException as exc:
            logger.error("Fatal Kafka error: %s", exc)
        finally:
            logger.info("Consumer shutting down — closing connection.")
            self._consumer.close()

    def stop(self) -> None:
        """Signal the consume loop to exit cleanly after the current poll."""
        self._running = False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _dispatch(self, msg: Any, handler: Callable[[dict], None]) -> None:
        """Decode message, call handler, commit on success."""
        topic = msg.topic()
        partition = msg.partition()
        offset = msg.offset()
        raw_key = msg.key().decode("utf-8") if msg.key() else None

        try:
            payload = json.loads(msg.value().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(
                "Failed to decode message | topic=%s | offset=%d | error=%s",
                topic, offset, exc,
            )
            self._send_to_dead_letter(msg, reason=str(exc))
            self._consumer.commit(message=msg, asynchronous=False)
            return

        retry_count = payload.get("_meta", {}).get("retry_count", 0)

        try:
            handler(payload)
            # Success — commit offset
            self._consumer.commit(message=msg, asynchronous=False)
            logger.debug(
                "Committed | topic=%s | partition=%d | offset=%d | key=%s",
                topic, partition, offset, raw_key,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Handler failed (retry %d/%d) | topic=%s | offset=%d | error=%s",
                retry_count + 1, self.MAX_RETRIES, topic, offset, exc,
            )
            if retry_count >= self.MAX_RETRIES - 1:
                logger.error(
                    "Max retries exceeded | topic=%s | offset=%d — sending to dead-letter",
                    topic, offset,
                )
                self._send_to_dead_letter(msg, reason=str(exc))
                self._consumer.commit(message=msg, asynchronous=False)
            # else: do NOT commit → message will be redelivered

    def _handle_error(self, error: Any) -> None:
        if error.code() == KafkaError._PARTITION_EOF:
            # End of partition — not an error, just no new messages
            logger.debug("Reached end of partition.")
        else:
            logger.error("Kafka consumer error: %s", error)

    def _send_to_dead_letter(self, msg: Any, reason: str) -> None:
        """Forward an unprocessable message to the dead-letter topic."""
        try:
            from backend.streaming.kafka_producer import NexoraProducer   # noqa: PLC0415
            from backend.streaming.topics import KafkaTopic                # noqa: PLC0415

            producer = NexoraProducer()
            raw = msg.value().decode("utf-8", errors="replace")
            try:
                original_payload = json.loads(raw)
            except json.JSONDecodeError:
                original_payload = {"raw": raw}

            producer.publish(
                topic=KafkaTopic.DEAD_LETTER,
                payload={
                    "original_topic": msg.topic(),
                    "original_offset": msg.offset(),
                    "failure_reason": reason,
                    "original_payload": original_payload,
                },
                key=msg.key().decode("utf-8") if msg.key() else None,
            )
            producer.flush(timeout=5.0)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send to dead-letter topic: %s", exc)

    def _build_consumer(self) -> Any:
        if not _KAFKA_AVAILABLE:
            return None

        conf = {
            "bootstrap.servers": self._bootstrap,
            "group.id": self._group_id,
            "client.id": f"nexora-consumer-{socket.gethostname()}",
            "auto.offset.reset": self._auto_offset_reset,
            "enable.auto.commit": False,      # manual commit after handler
            "max.poll.interval.ms": 300000,   # 5 min max processing time
            "session.timeout.ms": 30000,
            "heartbeat.interval.ms": 10000,
        }
        return Consumer(conf)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        logger.info("Received signal %d — stopping consumer.", signum)
        self.stop()
