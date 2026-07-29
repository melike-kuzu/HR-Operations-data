from __future__ import annotations

import logging

from workforce_assistant.domain.models import (
    RouteDecision,
)
from workforce_assistant.routing.llm_router import (
    route_question_with_llm,
)
from workforce_assistant.routing.rule_based_router import (
    route_question as route_question_with_rules,
)


logger = logging.getLogger(__name__)


def route_question(
    question: str,
) -> RouteDecision:
    """
    Route using Azure OpenAI.

    The existing rule-based router is retained only
    as a temporary fallback when Azure OpenAI is
    unavailable.
    """

    try:
        return route_question_with_llm(
            question
        )

    except Exception:
        logger.exception(
            "LLM routing failed. "
            "Using rule-based fallback."
        )

        return route_question_with_rules(
            question
        )