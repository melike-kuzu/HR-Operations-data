from __future__ import annotations

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

from workforce_assistant.config.settings import settings
from workforce_assistant.ingestion.index_schema import (
    build_workforce_index,
)


class IndexManager:
    def __init__(self) -> None:
        if not settings.azure_search_endpoint:
            raise ValueError(
                "AZURE_SEARCH_ENDPOINT is not configured."
            )

        if not settings.azure_search_api_key:
            raise ValueError(
                "AZURE_SEARCH_API_KEY is not configured."
            )

        self.index_name = settings.azure_search_index_name

        self.client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=AzureKeyCredential(
                settings.azure_search_api_key,
            ),
        )

    def create_or_update_index(self) -> None:
        index = build_workforce_index(
            index_name=self.index_name,
        )

        self.client.create_or_update_index(index)

        print(
            f"Index '{self.index_name}' is ready."
        )

    def index_exists(self) -> bool:
        index_names = self.client.list_index_names()

        return self.index_name in index_names

    def delete_index(self) -> None:
        if not self.index_exists():
            print(
                f"Index '{self.index_name}' does not exist."
            )
            return

        self.client.delete_index(
            self.index_name,
        )

        print(
            f"Index '{self.index_name}' was deleted."
        )