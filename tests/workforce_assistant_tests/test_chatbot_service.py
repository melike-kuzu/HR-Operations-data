import pandas as pd

from workforce_assistant.domain.models import RouteType
from workforce_assistant.repositories.search_repository import (
    InMemorySearchRepository,
    SearchDocument,
)
from workforce_assistant.services.chatbot_service import ChatbotService


def test_profile_search_uses_search_repository():
    repository = InMemorySearchRepository(
        [
            SearchDocument(
                id="1",
                title="Jane profile",
                content="Jane has Azure architecture experience.",
                source_type="profile",
            )
        ]
    )

    service = ChatbotService(search_repository=repository)
    response = service.ask("Show profile experience in Azure")

    assert response.route == RouteType.PROFILE_SEARCH
    assert response.sources[0]["id"] == "1"
