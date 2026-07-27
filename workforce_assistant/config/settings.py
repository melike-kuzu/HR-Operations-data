from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Local development configuration.
# In Docker/Azure, real environment variables take precedence.
load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


def _get_bool(
    variable_name: str,
    default: bool = False,
) -> bool:
    value = os.getenv(variable_name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str

    output_dir: Path
    document_dir: Path
    conversation_db_path: Path

    log_level: str
    log_format: str
    log_dir: Path
    enable_file_logging: bool

    chat_audit_enabled: bool
    admin_users: tuple[str, ...]

    local_user_id: str
    local_user_name: str

    azure_search_endpoint: str | None
    azure_search_index_name: str
    azure_search_api_key: str | None

    azure_openai_endpoint: str | None
    azure_openai_api_key: str | None
    azure_openai_chat_deployment: str | None
    azure_openai_embedding_deployment: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        output_dir = Path(
            os.getenv(
                "OUTPUT_DIR",
                str(PROJECT_ROOT / "output"),
            )
        )

        document_dir = Path(
            os.getenv(
                "DOCUMENT_DIR",
                str(PROJECT_ROOT / "data" / "documents"),
            )
        )

        conversation_db_path = Path(
            os.getenv(
                "CONVERSATION_DB_PATH",
                str(
                    PROJECT_ROOT
                    / "data"
                    / "runtime"
                    / "conversations.db"
                ),
            )
        )

        log_dir = Path(
            os.getenv(
                "LOG_DIR",
                str(PROJECT_ROOT / "logs"),
            )
        )

        admin_users = tuple(
            user.strip().lower()
            for user in os.getenv(
                "ADMIN_USERS",
                "",
            ).split(",")
            if user.strip()
        )

        return cls(
            app_name=os.getenv(
                "APP_NAME",
                "HR Decision Support Platform",
            ),
            environment=os.getenv(
                "APP_ENV",
                "local",
            ).lower(),
            output_dir=output_dir,
            document_dir=document_dir,
            conversation_db_path=conversation_db_path,
            log_level=os.getenv(
                "LOG_LEVEL",
                "INFO",
            ).upper(),
            log_format=os.getenv(
                "LOG_FORMAT",
                "json",
            ).lower(),
            log_dir=log_dir,
            enable_file_logging=_get_bool(
                "ENABLE_FILE_LOGGING",
                default=False,
            ),
            chat_audit_enabled=_get_bool(
                "CHAT_AUDIT_ENABLED",
                default=True,
            ),
            admin_users=admin_users,
            local_user_id=os.getenv(
                "LOCAL_USER_ID",
                "local.user",
            ).strip(),
            local_user_name=os.getenv(
                "LOCAL_USER_NAME",
                "Local User",
            ).strip(),
            azure_search_endpoint=os.getenv(
                "AZURE_SEARCH_ENDPOINT"
            ),
            azure_search_index_name=os.getenv(
                "AZURE_SEARCH_INDEX_NAME",
                "workforce-knowledge-index",
            ),
            azure_search_api_key=os.getenv(
                "AZURE_SEARCH_API_KEY"
            ),
            azure_openai_endpoint=os.getenv(
                "AZURE_OPENAI_ENDPOINT"
            ),
            azure_openai_api_key=os.getenv(
                "AZURE_OPENAI_API_KEY"
            ),
            azure_openai_chat_deployment=os.getenv(
                "AZURE_OPENAI_CHAT_DEPLOYMENT"
            ),
            azure_openai_embedding_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
            ),
        )


settings = Settings.from_environment()
