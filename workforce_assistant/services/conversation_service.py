from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from workforce_assistant.domain.conversation_models import (
    Conversation,
    ConversationMessage,
    MessageRole,
)
from workforce_assistant.repositories.conversation_repository import (
    ConversationRepository,
)


class ConversationService:
    """Application-level conversation operations."""

    def __init__(
        self,
        repository: ConversationRepository,
    ) -> None:
        self.repository = repository
        self.repository.initialise()

    def create_conversation(
        self,
        *,
        user_id: str,
        title: str = "New conversation",
    ) -> Conversation:
        cleaned_user_id = self._clean_required_text(
            user_id,
            field_name="user_id",
        )

        cleaned_title = self._clean_title(title)

        conversation = Conversation.create(
            user_id=cleaned_user_id,
            title=cleaned_title,
        )

        return self.repository.create_conversation(
            conversation
        )

    def get_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> Conversation | None:
        return self.repository.get_conversation(
            conversation_id,
            user_id=user_id,
        )

    def list_conversations(
        self,
        *,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Conversation]:
        return self.repository.list_conversations(
            user_id=user_id,
            include_archived=include_archived,
            limit=limit,
        )

    def get_messages(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> list[ConversationMessage]:
        return self.repository.list_messages(
            conversation_id,
            user_id=user_id,
        )

    def add_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: MessageRole,
        content: str,
        route: str | None = None,
        sources: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        conversation = self.repository.get_conversation(
            conversation_id,
            user_id=user_id,
        )

        if conversation is None:
            raise LookupError(
                "Conversation was not found or is not owned by the user."
            )

        cleaned_content = self._clean_required_text(
            content,
            field_name="content",
        )

        sequence_number = (
            self.repository.get_next_sequence_number(
                conversation_id
            )
        )

        message = ConversationMessage.create(
            conversation_id=conversation_id,
            role=role,
            content=cleaned_content,
            route=route,
            sources=sources,
            metadata=metadata,
            sequence_number=sequence_number,
        )

        saved_message = self.repository.add_message(
            message
        )

        if (
            role == "user"
            and conversation.title == "New conversation"
        ):
            conversation.title = self.generate_title(
                cleaned_content
            )
            conversation.updated_at = datetime.now(
                timezone.utc
            )
            self.repository.update_conversation(
                conversation
            )

        return saved_message

    def rename_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
        title: str,
    ) -> Conversation:
        conversation = self.repository.get_conversation(
            conversation_id,
            user_id=user_id,
        )

        if conversation is None:
            raise LookupError(
                "Conversation was not found or is not owned by the user."
            )

        conversation.title = self._clean_title(title)
        conversation.updated_at = datetime.now(
            timezone.utc
        )

        return self.repository.update_conversation(
            conversation
        )

    def archive_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> bool:
        return self.repository.archive_conversation(
            conversation_id,
            user_id=user_id,
        )

    @staticmethod
    def generate_title(
        first_user_message: str,
        *,
        maximum_length: int = 60,
    ) -> str:
        normalised = " ".join(
            first_user_message.split()
        )

        if len(normalised) <= maximum_length:
            return normalised

        shortened = normalised[
            : maximum_length - 1
        ].rstrip()

        return f"{shortened}…"

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = " ".join(title.split())

        if not cleaned:
            return "New conversation"

        if len(cleaned) > 120:
            return cleaned[:119].rstrip() + "…"

        return cleaned

    @staticmethod
    def _clean_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return cleaned