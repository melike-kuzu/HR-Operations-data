from pathlib import Path

import pytest

from workforce_assistant.repositories.sqlite_conversation_repository import (
    SQLiteConversationRepository,
)
from workforce_assistant.services.conversation_service import (
    ConversationService,
)


def create_service(
    tmp_path: Path,
) -> ConversationService:
    repository = SQLiteConversationRepository(
        tmp_path / "conversation-service.db"
    )
    return ConversationService(repository)


def test_create_conversation(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    assert conversation.user_id == "melike.local"
    assert conversation.title == "New conversation"


def test_first_user_message_generates_title(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    service.add_message(
        conversation_id=conversation.conversation_id,
        user_id="melike.local",
        role="user",
        content="Who is available for an Azure project?",
    )

    updated = service.get_conversation(
        conversation.conversation_id,
        user_id="melike.local",
    )

    assert updated is not None
    assert updated.title == (
        "Who is available for an Azure project?"
    )


def test_add_user_and_assistant_messages(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    service.add_message(
        conversation_id=conversation.conversation_id,
        user_id="melike.local",
        role="user",
        content="Show bench consultants.",
    )

    service.add_message(
        conversation_id=conversation.conversation_id,
        user_id="melike.local",
        role="assistant",
        content="There are four bench consultants.",
        route="bench_status",
        sources=["bench_status"],
        metadata={
            "response_time_ms": 92,
        },
    )

    messages = service.get_messages(
        conversation.conversation_id,
        user_id="melike.local",
    )

    assert len(messages) == 2
    assert messages[0].sequence_number == 1
    assert messages[1].sequence_number == 2
    assert messages[1].route == "bench_status"


def test_wrong_user_cannot_add_message(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    with pytest.raises(LookupError):
        service.add_message(
            conversation_id=conversation.conversation_id,
            user_id="another.user",
            role="user",
            content="This must not be stored.",
        )


def test_empty_message_is_rejected(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    with pytest.raises(
        ValueError,
        match="content cannot be empty",
    ):
        service.add_message(
            conversation_id=conversation.conversation_id,
            user_id="melike.local",
            role="user",
            content="   ",
        )


def test_rename_conversation(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    renamed = service.rename_conversation(
        conversation.conversation_id,
        user_id="melike.local",
        title="Azure staffing plan",
    )

    assert renamed.title == "Azure staffing plan"


def test_archive_conversation(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)

    conversation = service.create_conversation(
        user_id="melike.local"
    )

    result = service.archive_conversation(
        conversation.conversation_id,
        user_id="melike.local",
    )

    conversations = service.list_conversations(
        user_id="melike.local"
    )

    assert result is True
    assert conversations == []