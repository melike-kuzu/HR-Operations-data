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
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchDocument]:
        raise NotImplementedError


class InMemorySearchRepository(SearchRepository):
    def __init__(self, documents: list[SearchDocument] | None = None) -> None:
        self._documents = documents or []

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchDocument]:
        query_terms = set(query.lower().split())
        matches: list[tuple[int, SearchDocument]] = []

        for document in self._documents:
            haystack = f"{document.title or ''} {document.content}".lower()
            score = sum(term in haystack for term in query_terms)
            if score:
                matches.append((score, document))

        matches.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in matches[:top_k]]
