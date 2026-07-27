from __future__ import annotations

from functools import lru_cache

from workforce_assistant.config.settings import settings
from workforce_assistant.repositories.sqlite_conversation_repository import (
    SQLiteConversationRepository,
)
from workforce_assistant.services.conversation_service import (
    ConversationService,
)
from workforce_assistant.services.user_service import (
    UserService,
)


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    repository = SQLiteConversationRepository(
        settings.conversation_db_path
    )

    return ConversationService(repository)


@lru_cache(maxsize=1)
def get_user_service() -> UserService:
    return UserService(settings)