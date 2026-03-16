"""
Message Processor Worker — Nexora Customer Success Digital FTE.

Consumes inbound messages from all three channel Kafka topics
(gmail_incoming, whatsapp_incoming, webform_incoming), runs them through
the AI agent workflow, and publishes the result to agent_responses
(or escalations when escalated).

Run with:
    python -m workers.message_processor

Environment variables:
    KAFKA_BOOTSTRAP_SERVERS   default: localhost:9092
    KAFKA_CONSUMER_GROUP      default: nexora-message-processors
    DATABASE_URL              default: sqlite:///./nexora_support.db
    LLM_PROVIDER              default: anthropic
    ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY
    WORKER_CONCURRENCY        default: 1 (threads per process)
    LOG_LEVEL                 default: INFO
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any

# Ensure project root is on the Python path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.streaming.kafka_consumer import NexoraConsumer
from backend.streaming.kafka_producer import NexoraProducer
from backend.streaming.topics import KafkaTopic
from backend.database.database import SessionLocal, init_db
from backend.mcp.tool_registry import init_tools
from backend.services.knowledge_service import seed_all

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("workers.message_processor")

# ---------------------------------------------------------------------------
# Globals (initialised once at startup)
# ---------------------------------------------------------------------------

_producer: NexoraProducer | None = None
_lock = threading.Lock()


def _get_producer() -> NexoraProducer:
    global _producer
    with _lock:
        if _producer is None:
            _producer = NexoraProducer()
    return _producer


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


def process_message(payload: dict) -> None:
    """
    Handle one inbound message from any channel topic.

    Steps:
      1. Extract fields from Kafka payload
      2. Open a DB session
      3. Run the agent workflow
      4. Publish result to agent_responses or escalations
      5. Close DB session

    Raises on failure so the consumer does NOT commit the offset.
    """
    meta = payload.get("_meta", {})
    event_id = meta.get("event_id", "unknown")
    channel = payload.get("channel", "web_form")
    customer_id = payload.get("customer_id", "UNKNOWN")
    content = payload.get("content", "")

    logger.info(
        "Processing | event_id=%s | channel=%s | customer=%s",
        event_id, channel, customer_id,
    )

    start = time.monotonic()
    db = SessionLocal()

    try:
        from backend.agents.workflow import process_message as run_workflow  # noqa: PLC0415

        result = run_workflow(
            customer_id=customer_id,
            channel=channel,
            content=content,
            db=db,
            customer_name=payload.get("from_name", ""),
            customer_email=payload.get("from_email"),
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        producer = _get_producer()

        if result.get("escalated"):
            producer.publish_escalation(
                customer_id=customer_id,
                ticket_ref=result.get("ticket", {}).get("ticket_ref", ""),
                reason=result.get("escalation_reason", ""),
                severity=result.get("escalation_severity", "medium"),
                channel=channel,
                customer_name=result.get("customer", ""),
            )
        else:
            producer.publish_response(
                customer_id=customer_id,
                channel=channel,
                response_text=result.get("response", ""),
                ticket_ref=result.get("ticket", {}).get("ticket_ref"),
                escalated=False,
            )

        logger.info(
            "Completed | event_id=%s | intent=%s | kb=%s | ai=%s | %.1fms",
            event_id,
            result.get("intent", "?"),
            result.get("kb_used", False),
            result.get("ai_used", False),
            elapsed_ms,
        )

    except Exception as exc:
        logger.error("Workflow failed | event_id=%s | error=%s", event_id, exc)
        raise  # re-raise → consumer will retry or dead-letter

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logger.info("=== Nexora Message Processor Worker Starting ===")

    # One-time initialisation
    logger.info("Initialising database...")
    init_db()

    logger.info("Registering MCP tools...")
    init_tools()

    logger.info("Seeding knowledge base...")
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()

    group_id = os.getenv("KAFKA_CONSUMER_GROUP", "nexora-message-processors")
    consumer = NexoraConsumer(
        topics=list(KafkaTopic.INBOUND_TOPICS),
        group_id=group_id,
    )

    logger.info(
        "Subscribing to topics: %s | group: %s",
        [str(t) for t in KafkaTopic.INBOUND_TOPICS],
        group_id,
    )

    consumer.run(handler=process_message)
    logger.info("=== Message Processor Worker Stopped ===")


if __name__ == "__main__":
    main()
