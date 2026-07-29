from __future__ import annotations

import argparse
from pathlib import Path

from workforce_assistant.ingestion.index_manager import (
    IndexManager,
)
from workforce_assistant.ingestion.indexer import (
    DocumentIndexer,
)
from workforce_assistant.ingestion.models import (
    IngestionDocument,
)
from workforce_assistant.ingestion.profile_generator_reader import (
    build_profile_generator_documents,
)


DEFAULT_FILE = Path(
    "data/reference/profile_generator.xlsx"
)


def _batches(
    documents: list[IngestionDocument],
    batch_size: int,
):
    for start in range(
        0,
        len(documents),
        batch_size,
    ):
        yield documents[
            start:start + batch_size
        ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Index Profile Generator employee profiles "
            "into Azure AI Search."
        )
    )

    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help=(
            "Delete and recreate the Azure Search index "
            "before uploading."
        ),
    )

    arguments = parser.parse_args()

    if arguments.batch_size <= 0:
        raise ValueError(
            "batch-size must be positive."
        )

    manager = IndexManager()

    if arguments.recreate_index:
        manager.delete_index()

    manager.create_or_update_index()

    print(
        f"Reading Profile Generator: {arguments.file}"
    )

    documents = build_profile_generator_documents(
        arguments.file
    )

    print(
        f"Prepared {len(documents)} search document(s)."
    )

    if not documents:
        raise RuntimeError(
            "No documents were produced from Profile Generator."
        )

    unique_consultants = {
        document.consultant_name
        for document in documents
        if document.consultant_name
    }

    print(
        f"Current consultants represented: "
        f"{len(unique_consultants)}"
    )

    indexer = DocumentIndexer()
    uploaded = 0

    for batch_number, batch in enumerate(
        _batches(
            documents,
            arguments.batch_size,
        ),
        start=1,
    ):
        batch_count = indexer.index_documents(
            batch
        )
        uploaded += batch_count

        print(
            f"Batch {batch_number}: "
            f"uploaded {batch_count}; "
            f"total {uploaded}/{len(documents)}"
        )

    print(
        f"Completed. Uploaded {uploaded} document(s) "
        "to Azure AI Search."
    )


if __name__ == "__main__":
    main()