import os
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from dotenv import load_dotenv


load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def main() -> None:
    endpoint = require_env("AZURE_SEARCH_ENDPOINT")
    api_key = require_env("AZURE_SEARCH_API_KEY")
    expected_index = require_env(
        "AZURE_SEARCH_INDEX_NAME"
    )

    client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )

    index_names = list(client.list_index_names())

    print("Azure AI Search connection successful.")
    print(f"Endpoint: {endpoint}")
    print(f"Expected index: {expected_index}")

    if index_names:
        print("Existing indexes:")

        for index_name in index_names:
            print(f"- {index_name}")
    else:
        print("Existing indexes: none")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            "Azure AI Search connection failed: "
            f"{type(exc).__name__}: {exc}"
        )
        sys.exit(1)