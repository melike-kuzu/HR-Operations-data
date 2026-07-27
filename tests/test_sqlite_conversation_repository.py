from pathlib import Path

from workforce_assistant.domain.conversation_models import (
    Conversation,
    ConversationMessage,
)
from workforce_assistant.repositories.sqlite_conversation_repository import (
    SQLiteConversationRepository,
)


def create_repository(
    tmp_path: Path,
) -> SQLiteConversationRepository:
    repository = SQLiteConversationRepository(
        tmp_path / "conversations.db"
    )
    repository.initialise()
    return repository


def test_create_and_get_conversation(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    conversation = Conversation.create(
        user_id="melike.local",
        title="Bench planning",
    )

    repository.create_conversation(conversation)

    loaded = repository.get_conversation(
        conversation.conversation_id,
        user_id="melike.local",
    )

    assert loaded is not None
    assert loaded.conversation_id == (
        conversation.conversation_id
    )
    assert loaded.user_id == "melike.local"
    assert loaded.title == "Bench planning"


def test_user_cannot_access_another_users_conversation(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    conversation = Conversation.create(
        user_id="melike.local"
    )
    repository.create_conversation(conversation)

    loaded = repository.get_conversation(
        conversation.conversation_id,
        user_id="another.user",
    )

    assert loaded is None


def test_add_and_list_messages(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    conversation = Conversation.create(
        user_id="melike.local"
    )
    repository.create_conversation(conversation)

    user_message = ConversationMessage.create(
        conversation_id=conversation.conversation_id,
        role="user",
        content="Who is currently on the bench?",
        sequence_number=1,
    )

    assistant_message = ConversationMessage.create(
        conversation_id=conversation.conversation_id,
        role="assistant",
        content="Three consultants are currently on the bench.",
        sequence_number=2,
        route="bench_status",
        sources=["bench_status"],
        metadata={
            "response_time_ms": 125,
        },
    )

    repository.add_message(user_message)
    repository.add_message(assistant_message)

    messages = repository.list_messages(
        conversation.conversation_id,
        user_id="melike.local",
    )

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].route == "bench_status"
    assert messages[1].sources == ["bench_status"]
    assert (
        messages[1].metadata["response_time_ms"]
        == 125
    )


def test_list_conversations_returns_only_user_records(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    first = Conversation.create(
        user_id="melike.local",
        title="First",
    )
    second = Conversation.create(
        user_id="another.user",
        title="Second",
    )

    repository.create_conversation(first)
    repository.create_conversation(second)

    conversations = repository.list_conversations(
        user_id="melike.local"
    )

    assert len(conversations) == 1
    assert conversations[0].title == "First"


def test_archive_conversation(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path)

    conversation = Conversation.create(
        user_id="melike.local"
    )
    repository.create_conversation(conversation)

    archived = repository.archive_conversation(
        conversation.conversation_id,
        user_id="melike.local",
    )

    active_conversations = (
        repository.list_conversations(
            user_id="melike.local"
        )
    )

    all_conversations = (
        repository.list_conversations(
            user_id="melike.local",
            include_archived=True,
        )
    )

    assert archived is True
    assert active_conversations == []
    assert len(all_conversations) == 1
    assert all_conversations[0].is_archived is True