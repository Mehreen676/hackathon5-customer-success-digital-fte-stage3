"""
Kafka Topic Definitions — Nexora Customer Success Digital FTE.

Centralises all topic names so they are never hard-coded as strings
across the codebase.  Import KafkaTopic everywhere you need a topic name.

Topic design:
  - One inbound topic per channel  (gmail / whatsapp / webform)
  - One shared outbound topic for agent responses
  - Dedicated escalation topic so the escalation pipeline can be
    scaled and monitored independently
  - Dead-letter topic for messages that exceeded the retry limit

Retention / partition guidance (configure in k8s/configmap.yaml):
  gmail_incoming      → 6 partitions, 7-day retention
  whatsapp_incoming   → 12 partitions, 3-day retention  (higher volume)
  webform_incoming    → 3 partitions, 7-day retention
  agent_responses     → 6 partitions, 3-day retention
  escalations         → 3 partitions, 30-day retention  (audit trail)
  dead_letter         → 1 partition,  30-day retention
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Topic:
    """Immutable topic descriptor."""

    name: str
    description: str
    default_partitions: int = 3
    retention_days: int = 7

    def __str__(self) -> str:
        return self.name


class KafkaTopic:
    """Namespace of all Nexora Kafka topics."""

    GMAIL_INCOMING = _Topic(
        name="gmail_incoming",
        description="Inbound support emails normalised from Gmail API webhooks.",
        default_partitions=6,
        retention_days=7,
    )

    WHATSAPP_INCOMING = _Topic(
        name="whatsapp_incoming",
        description="Inbound WhatsApp messages from Twilio webhook.",
        default_partitions=12,
        retention_days=3,
    )

    WEBFORM_INCOMING = _Topic(
        name="webform_incoming",
        description="Inbound web-form submissions from the support portal.",
        default_partitions=3,
        retention_days=7,
    )

    AGENT_RESPONSES = _Topic(
        name="agent_responses",
        description="Outbound formatted responses produced by the AI agent workflow.",
        default_partitions=6,
        retention_days=3,
    )

    ESCALATIONS = _Topic(
        name="escalations",
        description="Escalation events for routing to human CS specialists.",
        default_partitions=3,
        retention_days=30,
    )

    DEAD_LETTER = _Topic(
        name="dead_letter",
        description="Messages that failed processing after all retry attempts.",
        default_partitions=1,
        retention_days=30,
    )

    # Convenience collections
    INBOUND_TOPICS: tuple[_Topic, ...] = (
        GMAIL_INCOMING,
        WHATSAPP_INCOMING,
        WEBFORM_INCOMING,
    )

    ALL_TOPICS: tuple[_Topic, ...] = (
        GMAIL_INCOMING,
        WHATSAPP_INCOMING,
        WEBFORM_INCOMING,
        AGENT_RESPONSES,
        ESCALATIONS,
        DEAD_LETTER,
    )

    @classmethod
    def names(cls) -> list[str]:
        """Return all topic names as strings."""
        return [t.name for t in cls.ALL_TOPICS]

    @classmethod
    def by_channel(cls, channel: str) -> _Topic:
        """
        Map a channel identifier to its inbound Kafka topic.

        Args:
            channel: "email" | "whatsapp" | "web_form"

        Returns:
            Matching _Topic instance.

        Raises:
            ValueError: if the channel is unknown.
        """
        mapping = {
            "email":    cls.GMAIL_INCOMING,
            "whatsapp": cls.WHATSAPP_INCOMING,
            "web_form": cls.WEBFORM_INCOMING,
        }
        if channel not in mapping:
            raise ValueError(
                f"Unknown channel {channel!r}. Valid options: {list(mapping)}"
            )
        return mapping[channel]
