from __future__ import annotations

from typing import Any

from workforce_assistant.config.settings import settings
from workforce_assistant.repositories.search_repository import (
    SearchDocument,
    SearchRepository,
)


class AzureSearchRepository(SearchRepository):
    """
    Azure AI Search adapter.

    This file is intentionally ready before credentials arrive.
    Install later:
        pip install azure-search-documents azure-identity
    """

    def __init__(self) -> None:
        if not settings.azure_search_endpoint:
            raise RuntimeError("AZURE_SEARCH_ENDPOINT is not configured.")

        if not settings.azure_search_api_key:
            raise RuntimeError("AZURE_SEARCH_API_KEY is not configured.")

        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure Search packages are not installed. "
                "Install azure-search-documents and azure-core."
            ) from exc

        self._client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=AzureKeyCredential(settings.azure_search_api_key),
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchDocument]:
        filter_expression = self._build_filter_expression(filters)

        results = self._client.search(
            search_text=query,
            top=top_k,
            filter=filter_expression,
            select=[
                "id",
                "content",
                "title",
                "source_type",
                "source_file",
                "consultant_name",
                "page_number",
            ],
        )

        documents: list[SearchDocument] = []
        for result in results:
            documents.append(
                SearchDocument(
                    id=str(result["id"]),
                    content=result.get("content", ""),
                    title=result.get("title"),
                    source_type=result.get("source_type"),
                    source_file=result.get("source_file"),
                    consultant_name=result.get("consultant_name"),
                    page_number=result.get("page_number"),
                    score=result.get("@search.score"),
                    metadata=dict(result),
                )
            )

        return documents

    @staticmethod
    def _build_filter_expression(
        filters: dict[str, Any] | None,
    ) -> str | None:
        if not filters:
            return None

        expressions = []
        for key, value in filters.items():
            if value is None:
                continue
            safe_value = str(value).replace("'", "''")
            expressions.append(f"{key} eq '{safe_value}'")

        return " and ".join(expressions) or None
