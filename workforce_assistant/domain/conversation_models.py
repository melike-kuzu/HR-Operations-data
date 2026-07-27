from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


MessageRole = Literal["user", "assistant", "system"]


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Conversation:
    conversation_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False
    last_route: str | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        title: str = "New conversation",
    ) -> "Conversation":
        now = utc_now()

        return cls(
            conversation_id=str(uuid4()),
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class ConversationMessage:
    message_id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    sequence_number: int
    route: str | None = None
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        conversation_id: str,
        role: MessageRole,
        content: str,
        sequence_number: int,
        route: str | None = None,
        sources: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ConversationMessage":
        return cls(
            message_id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=utc_now(),
            sequence_number=sequence_number,
            route=route,
            sources=list(sources or []),
            metadata=dict(metadata or {}),
        )