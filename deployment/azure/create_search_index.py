from workforce_assistant.ingestion.index_manager import IndexManager


def main() -> None:
    manager = IndexManager()
    manager.create_or_update_index()


if __name__ == "__main__":
    main()