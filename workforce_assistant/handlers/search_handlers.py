from __future__ import annotations

from workforce_assistant.domain.models import ChatResponse, RouteType
from workforce_assistant.repositories.search_repository import SearchRepository


def handle_search_route(
    question: str,
    route_type: RouteType,
    search_repository: SearchRepository,
) -> ChatResponse:
    source_filter = {
        RouteType.PROFILE_SEARCH: {"source_type": "profile"},
        RouteType.DOCUMENT_SEARCH: None,
    }.get(route_type)

    documents = search_repository.search(
        question,
        top_k=5,
        filters=source_filter,
    )

    if not documents:
        return ChatResponse(
            answer="No relevant indexed content was found.",
            route=route_type,
        )

    answer = "\n\n".join(
        f"- {document.title or document.source_file or document.id}: "
        f"{document.content[:300]}"
        for document in documents
    )

    return ChatResponse(
        answer=answer,
        route=route_type,
        sources=[
            {
                "id": document.id,
                "title": document.title,
                "source_file": document.source_file,
                "page_number": document.page_number,
                "score": document.score,
            }
            for document in documents
        ],
    )
