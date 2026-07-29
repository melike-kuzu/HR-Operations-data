from __future__ import annotations

from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from workforce_assistant.config.settings import settings
from workforce_assistant.repositories.search_repository import (
    SearchDocument,
    SearchRepository,
)


SEMANTIC_CONFIGURATION_NAME = "workforce-semantic-config"
VECTOR_FIELD_NAME = "content_vector"
VECTOR_DIMENSIONS = 1536


class AzureSearchRepository(SearchRepository):
    """
    Azure AI Search repository using hybrid retrieval:

    - keyword search
    - vector similarity search
    - semantic ranking
    """

    def __init__(self) -> None:
        self._validate_settings()

        self._search_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=AzureKeyCredential(
                settings.azure_search_api_key,
            ),
        )

        self._openai_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01",
        )

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchDocument]:
        clean_query = query.strip()

        if not clean_query:
            raise ValueError(
                "Search query cannot be empty."
            )

        if top_k is not None and top_k < 1:
            raise ValueError(
                "top_k must be greater than zero or None."
            )

        result_limit = top_k or 30

        filter_expression = self._build_filter_expression(
            filters
        )

        query_embedding = self._create_query_embedding(
            clean_query
        )

        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=max(
                result_limit,
                30,
            ),
            fields=VECTOR_FIELD_NAME,
        )

        results = self._search_client.search(
            search_text=clean_query,
            vector_queries=[vector_query],
            query_type="semantic",
            semantic_configuration_name=(
                SEMANTIC_CONFIGURATION_NAME
            ),
            filter=filter_expression,
            top=result_limit,
            include_total_count=True,
            select=[
                "id",
                "record_type",
                "consultant_id",
                "consultant_name",
                "content",
                "title",
                "source_type",
                "source_file",
                "sheet_name",
                "row_number",
                "skills",
                "level",
                "group",
                "client",
                "page_number",
                "chunk_id",
                "is_active",
                "last_modified",
            ],
        )

        documents: list[SearchDocument] = []

        for result in results:
            documents.append(
                SearchDocument(
                    id=str(result["id"]),
                    content=result.get(
                        "content",
                        "",
                    ),
                    title=result.get("title"),
                    source_type=result.get(
                        "source_type"
                    ),
                    source_file=result.get(
                        "source_file"
                    ),
                    consultant_name=result.get(
                        "consultant_name"
                    ),
                    page_number=result.get(
                        "page_number"
                    ),
                    score=result.get(
                        "@search.reranker_score"
                    )
                    or result.get(
                        "@search.score"
                    ),
                    metadata=dict(result),
                )
            )

        return documents

    def _create_query_embedding(
        self,
        query: str,
    ) -> list[float]:
        response = (
            self._openai_client.embeddings.create(
                model=(
                    settings
                    .azure_openai_embedding_deployment
                ),
                input=query,
            )
        )

        embedding = response.data[0].embedding

        if len(embedding) != VECTOR_DIMENSIONS:
            raise ValueError(
                "Query embedding dimension does not "
                "match the Azure Search index. "
                f"Expected {VECTOR_DIMENSIONS}, "
                f"received {len(embedding)}."
            )

        return embedding

    @staticmethod
    def _build_filter_expression(
        filters: dict[str, Any] | None,
    ) -> str | None:
        if not filters:
            return None

        expressions: list[str] = []

        for key, value in filters.items():
            if value is None:
                continue

            if isinstance(value, bool):
                expressions.append(
                    f"{key} eq {str(value).lower()}"
                )
                continue

            if isinstance(value, (int, float)):
                expressions.append(
                    f"{key} eq {value}"
                )
                continue

            if isinstance(
                value,
                (list, tuple, set),
            ):
                values = [
                    str(item).replace(
                        "'",
                        "''",
                    )
                    for item in value
                ]

                if not values:
                    continue

                value_expression = " or ".join(
                    f"{key} eq '{item}'"
                    for item in values
                )

                expressions.append(
                    f"({value_expression})"
                )
                continue

            safe_value = str(value).replace(
                "'",
                "''",
            )

            expressions.append(
                f"{key} eq '{safe_value}'"
            )

        return " and ".join(
            expressions
        ) or None

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
            for name, value
            in required_settings.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )