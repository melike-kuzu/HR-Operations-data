from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from workforce_assistant.domain.conversation_models import (
    Conversation,
    ConversationMessage,
)


class SQLiteConversationRepository:
    """SQLite implementation of conversation persistence."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=15,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        return connection

    def initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_archived INTEGER NOT NULL DEFAULT 0,
                    last_route TEXT
                );

                CREATE INDEX IF NOT EXISTS
                    idx_conversations_user_updated
                ON conversations (
                    user_id,
                    is_archived,
                    updated_at DESC
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL
                        CHECK (role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    route TEXT,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    FOREIGN KEY (conversation_id)
                        REFERENCES conversations(conversation_id)
                        ON DELETE CASCADE,
                    UNIQUE (
                        conversation_id,
                        sequence_number
                    )
                );

                CREATE INDEX IF NOT EXISTS
                    idx_messages_conversation_sequence
                ON messages (
                    conversation_id,
                    sequence_number
                );
                """
            )

    def create_conversation(
        self,
        conversation: Conversation,
    ) -> Conversation:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    conversation_id,
                    user_id,
                    title,
                    created_at,
                    updated_at,
                    is_archived,
                    last_route
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation.conversation_id,
                    conversation.user_id,
                    conversation.title,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                    int(conversation.is_archived),
                    conversation.last_route,
                ),
            )

        return conversation

    def get_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    conversation_id,
                    user_id,
                    title,
                    created_at,
                    updated_at,
                    is_archived,
                    last_route
                FROM conversations
                WHERE conversation_id = ?
                  AND user_id = ?
                """,
                (
                    conversation_id,
                    user_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._conversation_from_row(row)

    def list_conversations(
        self,
        *,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Conversation]:
        if limit < 1:
            return []

        query = """
            SELECT
                conversation_id,
                user_id,
                title,
                created_at,
                updated_at,
                is_archived,
                last_route
            FROM conversations
            WHERE user_id = ?
        """

        parameters: list[object] = [user_id]

        if not include_archived:
            query += " AND is_archived = 0"

        query += " ORDER BY updated_at DESC LIMIT ?"
        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            self._conversation_from_row(row)
            for row in rows
        ]

    def update_conversation(
        self,
        conversation: Conversation,
    ) -> Conversation:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE conversations
                SET
                    title = ?,
                    updated_at = ?,
                    is_archived = ?,
                    last_route = ?
                WHERE conversation_id = ?
                  AND user_id = ?
                """,
                (
                    conversation.title,
                    conversation.updated_at.isoformat(),
                    int(conversation.is_archived),
                    conversation.last_route,
                    conversation.conversation_id,
                    conversation.user_id,
                ),
            )

            if cursor.rowcount == 0:
                raise LookupError(
                    "Conversation was not found or is not owned by the user."
                )

        return conversation

    def archive_conversation(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE conversations
                SET
                    is_archived = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = ?
                  AND user_id = ?
                """,
                (
                    conversation_id,
                    user_id,
                ),
            )

        return cursor.rowcount > 0

    def add_message(
        self,
        message: ConversationMessage,
    ) -> ConversationMessage:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    route,
                    sources_json,
                    metadata_json,
                    created_at,
                    sequence_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.conversation_id,
                    message.role,
                    message.content,
                    message.route,
                    json.dumps(
                        message.sources,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        message.metadata,
                        ensure_ascii=False,
                        default=str,
                    ),
                    message.created_at.isoformat(),
                    message.sequence_number,
                ),
            )

            connection.execute(
                """
                UPDATE conversations
                SET
                    updated_at = ?,
                    last_route = COALESCE(?, last_route)
                WHERE conversation_id = ?
                """,
                (
                    message.created_at.isoformat(),
                    message.route,
                    message.conversation_id,
                ),
            )

        return message

    def list_messages(
        self,
        conversation_id: str,
        *,
        user_id: str,
    ) -> list[ConversationMessage]:
        with self._connect() as connection:
            owner = connection.execute(
                """
                SELECT 1
                FROM conversations
                WHERE conversation_id = ?
                  AND user_id = ?
                """,
                (
                    conversation_id,
                    user_id,
                ),
            ).fetchone()

            if owner is None:
                return []

            rows = connection.execute(
                """
                SELECT
                    message_id,
                    conversation_id,
                    role,
                    content,
                    route,
                    sources_json,
                    metadata_json,
                    created_at,
                    sequence_number
                FROM messages
                WHERE conversation_id = ?
                ORDER BY sequence_number ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [
            self._message_from_row(row)
            for row in rows
        ]

    def get_next_sequence_number(
        self,
        conversation_id: str,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(MAX(sequence_number), 0) + 1
                        AS next_sequence_number
                FROM messages
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return int(row["next_sequence_number"])

    @staticmethod
    def _conversation_from_row(
        row: sqlite3.Row,
    ) -> Conversation:
        return Conversation(
            conversation_id=row["conversation_id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"]
            ),
            is_archived=bool(row["is_archived"]),
            last_route=row["last_route"],
        )

    @staticmethod
    def _message_from_row(
        row: sqlite3.Row,
    ) -> ConversationMessage:
        return ConversationMessage(
            message_id=row["message_id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            route=row["route"],
            sources=json.loads(
                row["sources_json"] or "[]"
            ),
            metadata=json.loads(
                row["metadata_json"] or "{}"
            ),
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
            sequence_number=int(
                row["sequence_number"]
            ),
        )