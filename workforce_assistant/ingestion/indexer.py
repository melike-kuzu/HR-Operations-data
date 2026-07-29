from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from workforce_assistant.config.settings import settings
from workforce_assistant.ingestion.models import IngestionDocument


class DocumentIndexer:
    """
    Creates embeddings with Azure OpenAI and uploads documents
    to Azure AI Search.
    """

    def __init__(self) -> None:
        self._validate_settings()

        self._openai_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01",
        )

        self._search_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=AzureKeyCredential(
                settings.azure_search_api_key,
            ),
        )

    def index_documents(
        self,
        documents: Iterable[IngestionDocument],
    ) -> int:
        source_documents = list(documents)

        if not source_documents:
            return 0

        search_documents = [
            self._build_search_document(document)
            for document in source_documents
        ]

        results = self._search_client.upload_documents(
            documents=search_documents,
        )

        failed_results = [
            result
            for result in results
            if not result.succeeded
        ]

        if failed_results:
            errors = "; ".join(
                f"{result.key}: {result.error_message}"
                for result in failed_results
            )

            raise RuntimeError(
                f"Some documents could not be indexed: {errors}"
            )

        return len(results)

    def _build_search_document(
        self,
        document: IngestionDocument,
    ) -> dict[str, Any]:
        metadata = document.metadata

        return {
            "id": document.id,
            "record_type": str(
                metadata.get("record_type", "document_chunk")
            ),
            "consultant_id": self._optional_string(
                metadata.get("consultant_id")
            ),
            "consultant_name": document.consultant_name,
            "title": document.title,
            "content": document.content,
            "content_vector": self._create_embedding(
                document.content
            ),
            "skills": self._normalise_skills(
                metadata.get("skills")
            ),
            "level": self._optional_string(
                metadata.get("level")
            ),
            "group": self._optional_string(
                metadata.get("group")
            ),
            "client": self._optional_string(
                metadata.get("client")
            ),
            "source_type": document.source_type,
            "source_file": document.source_file,
            "sheet_name": self._optional_string(
                metadata.get("sheet_name")
            ),
            "row_number": self._optional_integer(
                metadata.get("row_number")
            ),
            "page_number": document.page_number,
            "chunk_id": self._optional_string(
                metadata.get("chunk_id", document.id)
            ),
            "is_active": self._normalise_boolean(
                metadata.get("is_active", True)
            ),
            "last_modified": self._normalise_datetime(
                metadata.get("last_modified")
            ),
        }

    def _create_embedding(
        self,
        content: str,
    ) -> list[float]:
        clean_content = content.strip()

        if not clean_content:
            raise ValueError(
                "Cannot create an embedding for empty content."
            )

        response = self._openai_client.embeddings.create(
            model=settings.azure_openai_embedding_deployment,
            input=clean_content,
        )

        embedding = response.data[0].embedding

        if len(embedding) != 1536:
            raise ValueError(
                "Embedding dimension does not match the "
                f"Azure Search index. Expected 1536, "
                f"received {len(embedding)}."
            )

        return embedding

    @staticmethod
    def _normalise_skills(
        value: Any,
    ) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            return [
                skill.strip()
                for skill in value.split(",")
                if skill.strip()
            ]

        if isinstance(value, (list, tuple, set)):
            return [
                str(skill).strip()
                for skill in value
                if str(skill).strip()
            ]

        return [str(value).strip()]

    @staticmethod
    def _optional_string(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalised = str(value).strip()
        return normalised or None

    @staticmethod
    def _optional_integer(
        value: Any,
    ) -> int | None:
        if value is None or value == "":
            return None

        return int(value)

    @staticmethod
    def _normalise_boolean(
        value: Any,
    ) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {
                "1",
                "true",
                "yes",
                "active",
            }

        return bool(value)

    @staticmethod
    def _normalise_datetime(
        value: Any,
    ) -> str:
        if value is None:
            return datetime.now(
                timezone.utc
            ).isoformat()

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(
                    tzinfo=timezone.utc
                )

            return value.isoformat()

        return str(value)

    @staticmethod
    def _validate_settings() -> None:
        required_settings = {
            "AZURE_SEARCH_ENDPOINT":
                settings.azure_search_endpoint,
            "AZURE_SEARCH_API_KEY":
                settings.azure_search_api_key,
            "AZURE_SEARCH_INDEX_NAME":
                settings.azure_search_index_name,
            "AZURE_OPENAI_ENDPOINT":
                settings.azure_openai_endpoint,
            "AZURE_OPENAI_API_KEY":
                settings.azure_openai_api_key,
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT":
                settings.azure_openai_embedding_deployment,
        }

        missing = [
            name
            for name, value in required_settings.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )