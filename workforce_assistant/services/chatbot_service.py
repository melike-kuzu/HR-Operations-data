from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from workforce_assistant.domain.models import (
    ChatResponse,
    RouteType,
)
from workforce_assistant.handlers.search_handlers import (
    handle_search_route,
)
from workforce_assistant.handlers.structured_handlers import (
    REPORT_BY_ROUTE,
    handle_structured_route,
)
from workforce_assistant.repositories.azure_search_repository import (
    AzureSearchRepository,
)
from workforce_assistant.repositories.search_repository import (
    InMemorySearchRepository,
    SearchRepository,
)
from workforce_assistant.routing.router import (
    route_question,
)


logger = logging.getLogger(__name__)


class ChatbotService:
    def __init__(
        self,
        search_repository: SearchRepository | None = None,
    ) -> None:
        if search_repository is not None:
            self._search_repository = search_repository
        else:
            try:
                self._search_repository = (
                    AzureSearchRepository()
                )
            except Exception:
                logger.exception(
                    "Azure Search could not be initialised. "
                    "Falling back to in-memory search."
                )
                self._search_repository = (
                    InMemorySearchRepository()
                )

    def ask(
        self,
        question: str,
        *,
        request_id: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> ChatResponse:
        current_request_id = (
            request_id or str(uuid4())
        )
        start_time = perf_counter()

        logger.info(
            "Chat request received",
            extra={
                "event_type": "chat_request_started",
                "request_id": current_request_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "question": question,
                "question_length": len(question),
            },
        )

        try:
            decision = route_question(question)
            route_type = decision.route_type

            if route_type in REPORT_BY_ROUTE:
                response = handle_structured_route(
                    route_type,
                    question,
                )





            elif route_type in {
                RouteType.SKILL_LOOKUP,
                RouteType.PROFILE_SEARCH,
                RouteType.DOCUMENT_SEARCH,
            }:
                search_route_type = route_type

                if route_type == RouteType.SKILL_LOOKUP:
                    search_route_type = (
                        RouteType.PROFILE_SEARCH
                    )

                response = handle_search_route(
                    question,
                    search_route_type,
                    self._search_repository,
                    extracted_filters=decision.extracted_filters,
                )

            else:
                response = ChatResponse(
                    answer=(
                        "I could not confidently identify "
                        "the required data source."
                    ),
                    route=RouteType.UNKNOWN,
                )

            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            response.metadata[
                "request_id"
            ] = current_request_id
            response.metadata[
                "router_confidence"
            ] = decision.confidence
            response.metadata[
                "extracted_filters"
            ] = decision.extracted_filters
            response.metadata[
                "response_time_ms"
            ] = duration_ms

            logger.info(
                "Chat request completed",
                extra={
                    "event_type": (
                        "chat_request_completed"
                    ),
                    "request_id": current_request_id,
                    "user_id": user_id,
                    "conversation_id": (
                        conversation_id
                    ),
                    "question": question,
                    "answer": response.answer,
                    "route": route_type.value,
                    "router_confidence": (
                        decision.confidence
                    ),
                    "response_time_ms": duration_ms,
                    "report_name": response.metadata.get(
                        "report_name"
                    ),
                    "filters": response.metadata.get(
                        "filters",
                        {},
                    ),
                    "table_row_count": response.metadata.get(
                        "table_row_count"
                    ),
                    "source_count": len(
                        response.sources
                    ),
                    "sources": response.sources,
                    "table_count": len(
                        response.tables
                    ),
                    "success": True,
                },
            )

            return response

        except Exception:
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "Chat request failed",
                extra={
                    "event_type": (
                        "chat_request_failed"
                    ),
                    "request_id": current_request_id,
                    "user_id": user_id,
                    "conversation_id": (
                        conversation_id
                    ),
                    "question": question,
                    "response_time_ms": duration_ms,
                    "success": False,
                },
            )

            raise


_default_service = ChatbotService()


def ask_data_question(
    question: str,
    *,
    user_id: str | None = None,
    conversation_id: str | None = None,
) -> dict:
    response = _default_service.ask(
        question,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    return {
        "answer": response.answer,
        "route": response.route.value,
        "tables": response.tables,
        "sources": response.sources,
        "metadata": response.metadata,
    }