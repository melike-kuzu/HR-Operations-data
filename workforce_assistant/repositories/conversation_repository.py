from __future__ import annotations

from typing import Protocol

from workforce_assistant.domain.conversation_models import (
    Conversation,
    ConversationMessage,
)


class ConversationRepository(Protocol):
    """Persistence contract for conversations and messages."""

    def initialise(self) -> None:
        """Create required persistence structures."""

    def create_conversation(
        self,
        conversation: Conversation,
    ) -> Conversation:
        """Persist and return a conversation."""

    def get_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> Conversation | None:
        """Return one conversation owned by the user."""

    def list_conversations(
        self,
        *,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Conversation]:
        """Return the user's conversations ordered by recent activity."""

    def update_conversation(
        self,
        conversation: Conversation,
    ) -> Conversation:
        """Persist mutable conversation fields."""

    def archive_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> bool:
        """Archive a conversation owned by the user."""

    def add_message(
        self,
        message: ConversationMessage,
    ) -> ConversationMessage:
        """Persist one conversation message."""

    def list_messages(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> list[ConversationMessage]:
        """Return messages after validating conversation ownership."""

    def get_next_sequence_number(
        self,
        conversation_id: str,
    ) -> int:
        """Return the next message sequence number."""