from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchDocument:
    id: str
    content: str
    title: str | None = None
    source_type: str | None = None
    source_file: str | None = None
    consultant_name: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] | None = None
    score: float | None = None


class SearchRepository(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchDocument]:
        """
        Search indexed documents.

        top_k=None:
            Return all matching documents.

        top_k=<number>:
            Return at most the requested number of documents.
        """
        raise NotImplementedError


class InMemorySearchRepository(SearchRepository):
    def __init__(
        self,
        documents: list[SearchDocument] | None = None,
    ) -> None:
        self._documents = documents or []

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchDocument]:
        query_terms = set(query.lower().split())
        matches: list[tuple[int, SearchDocument]] = []

        for document in self._documents:
            if not self._matches_filters(document, filters):
                continue

            haystack = (
                f"{document.title or ''} "
                f"{document.content} "
                f"{document.consultant_name or ''}"
            ).lower()

            score = sum(
                term in haystack
                for term in query_terms
            )

            if score:
                matches.append((score, document))

        matches.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        documents = [
            document
            for _, document in matches
        ]

        if top_k is None:
            return documents

        if top_k < 1:
            raise ValueError(
                "top_k must be greater than zero or None."
            )

        return documents[:top_k]

    @staticmethod
    def _matches_filters(
        document: SearchDocument,
        filters: dict[str, Any] | None,
    ) -> bool:
        if not filters:
            return True

        metadata = document.metadata or {}

        for key, expected_value in filters.items():
            if expected_value is None:
                continue

            if key == "consultant_name":
                actual_value = document.consultant_name
            elif key == "source_type":
                actual_value = document.source_type
            elif key == "source_file":
                actual_value = document.source_file
            elif key == "page_number":
                actual_value = document.page_number
            else:
                actual_value = metadata.get(key)

            if actual_value != expected_value:
                return False

        return True