from pathlib import Path

from workforce_assistant.config.settings import (
    Settings,
)
from workforce_assistant.services.user_service import (
    UserService,
)


def create_settings() -> Settings:
    return Settings(
        app_name="Test",
        environment="test",
        output_dir=Path("output"),
        document_dir=Path("documents"),
        conversation_db_path=Path(
            "conversations.db"
        ),
        log_level="INFO",
        log_format="json",
        log_dir=Path("logs"),
        enable_file_logging=False,
        chat_audit_enabled=True,
        admin_users=(
            "melike.local",
        ),
        local_user_id="Melike.Local",
        local_user_name="Melike",
        azure_search_endpoint=None,
        azure_search_index_name="test-index",
        azure_search_api_key=None,
        azure_openai_endpoint=None,
        azure_openai_api_key=None,
        azure_openai_chat_deployment=None,
        azure_openai_embedding_deployment=None,
    )


def test_get_current_local_user() -> None:
    service = UserService(
        create_settings()
    )

    user = service.get_current_user()

    assert user.user_id == "melike.local"
    assert user.display_name == "Melike"
    assert user.is_admin is True