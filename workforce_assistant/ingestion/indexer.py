from __future__ import annotations

from collections.abc import Iterable

from workforce_assistant.ingestion.models import IngestionDocument


class DocumentIndexer:
    """
    Placeholder indexing boundary.

    Later this class will:
    1. create embeddings through Azure OpenAI,
    2. upload chunks to Azure AI Search,
    3. update only changed documents.
    """

    def index_documents(
        self,
        documents: Iterable[IngestionDocument],
    ) -> int:
        return sum(1 for _ in documents)
