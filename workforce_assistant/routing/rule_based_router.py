from __future__ import annotations

import re

from workforce_assistant.domain.models import (
    RouteDecision,
    RouteType,
)


PERSON_LOOKUP_TERMS = (
    "who",
    "which consultant",
    "which consultants",
    "which employee",
    "which employees",
    "find someone",
    "find a consultant",
    "find consultants",
    "find an employee",
    "find employees",
    "show people",
    "show consultants",
    "show employees",
    "looking for someone",
    "need someone",
    "need a consultant",
)

SKILL_INTENT_TERMS = (
    "know",
    "knows",
    "has experience",
    "have experience",
    "experience in",
    "experienced in",
    "experience with",
    "experienced with",
    "knowledge of",
    "knowledge in",
    "skilled in",
    "skilled with",
    "skills in",
    "worked with",
    "familiar with",
    "expert in",
    "expertise in",
    "qualified in",
    "certified in",
)

PROFILE_TERMS = (
    "profile",
    "cv",
    "résumé",
    "resume",
    "professional experience",
    "project experience",
    "career history",
    "employment history",
    "background",
    "tell me about",
    "summarise",
    "summarize",
)


def _normalise_question(question: str) -> str:
    normalised = question.strip().lower()
    normalised = re.sub(
        r"\s+",
        " ",
        normalised,
    )
    return normalised


def _contains_any(
    question: str,
    terms: tuple[str, ...],
) -> bool:
    return any(
        term in question
        for term in terms
    )


def _is_skill_lookup(
    question: str,
) -> bool:
    has_person_intent = _contains_any(
        question,
        PERSON_LOOKUP_TERMS,
    )

    has_skill_intent = _contains_any(
        question,
        SKILL_INTENT_TERMS,
    )

    dynamic_skill_patterns = (
        r"\bhas\s+.+?\s+experience\b",
        r"\bhave\s+.+?\s+experience\b",
        r"\bknows?\s+.+",
        r"\bexperienced\s+(?:in|with)\s+.+",
        r"\bskilled\s+(?:in|with)\s+.+",
        r"\bexpert\s+in\s+.+",
        r"\bcertified\s+in\s+.+",
        r"\bqualified\s+in\s+.+",
    )

    has_dynamic_skill_intent = any(
        re.search(
            pattern,
            question,
        )
        for pattern in dynamic_skill_patterns
    )

    return (
        has_person_intent
        and (
            has_skill_intent
            or has_dynamic_skill_intent
        )
    )


def _extract_skill_query(
    question: str,
) -> str | None:
    patterns = (
        (
            r"\b(?:who|which consultant|which consultants|"
            r"which employee|which employees)"
            r"\s+(?:has|have)\s+"
            r"(.+?)\s+experience\b"
        ),
        (
            r"\b(?:who|which consultant|which consultants|"
            r"which employee|which employees)"
            r"\s+knows?\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bexperience\s+(?:in|with)\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bexperienced\s+(?:in|with)\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bskilled\s+(?:in|with)\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bexpert(?:ise)?\s+in\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bknowledge\s+(?:of|in)\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bworked\s+with\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\bfamiliar\s+with\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
        (
            r"\b(?:qualified|certified)\s+in\s+"
            r"(.+?)(?:\s+and\b|\?|$)"
        ),
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            question,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        skill_query = match.group(1).strip(
            " ?,.!"
        )

        if skill_query:
            return skill_query

    return None


def _extract_availability_filter(
    question: str,
) -> str | None:
    next_month_terms = (
        "available next month",
        "availability next month",
        "free next month",
        "on bench next month",
        "bench next month",
    )

    if _contains_any(
        question,
        next_month_terms,
    ):
        return "next_month"

    bench_terms = (
        "on bench",
        "currently on bench",
        "is on bench",
        "are on bench",
        "benched",
    )

    if _contains_any(
        question,
        bench_terms,
    ):
        return "bench"

    return None


def _extract_active_projects_filter(
    question: str,
) -> dict[str, object] | None:
    patterns = (
        (
            r"(?:less than|fewer than|under)\s+"
            r"(\d+)\s+active projects?"
        ),
        (
            r"active projects?\s+"
            r"(?:less than|fewer than|under)\s+"
            r"(\d+)"
        ),
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            question,
        )

        if match:
            return {
                "operator": "lt",
                "value": int(
                    match.group(1)
                ),
            }

    no_project_terms = (
        "no active projects",
        "without active projects",
        "zero active projects",
    )

    if _contains_any(
        question,
        no_project_terms,
    ):
        return {
            "operator": "eq",
            "value": 0,
        }

    return None


def _extract_group_filter(
    question: str,
) -> str | None:
    patterns = (
        r"\bin\s+the\s+(.+?)\s+group\b",
        r"\bfrom\s+the\s+(.+?)\s+group\b",
        r"\bgroup\s+(?:is|=|called)\s+(.+?)(?:\?|$)",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            question,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        group_name = match.group(1).strip(
            " ?,.!"
        )

        if group_name:
            return group_name

    return None


def _extract_filters(
    question: str,
) -> dict[str, object]:
    filters: dict[str, object] = {}

    skill_query = _extract_skill_query(
        question
    )

    if skill_query:
        filters["skill_query"] = skill_query

    availability = (
        _extract_availability_filter(
            question
        )
    )

    if availability:
        filters["availability"] = (
            availability
        )

    active_projects = (
        _extract_active_projects_filter(
            question
        )
    )

    if active_projects:
        filters["active_projects"] = (
            active_projects
        )

    group_name = _extract_group_filter(
        question
    )

    if group_name:
        filters["group"] = group_name

    return filters


def route_question(
    question: str,
) -> RouteDecision:
    q = _normalise_question(question)

    extracted_filters = _extract_filters(
        q
    )

    # Skill/person searches are checked first.
    #
    # This ensures a combined question such as:
    # "Who knows Azure and is on bench?"
    #
    # is routed to profile search instead of only
    # returning the complete bench report.
    if _is_skill_lookup(q):
        return RouteDecision(
            route_type=RouteType.SKILL_LOOKUP,
            confidence=0.96,
            extracted_filters=extracted_filters,
        )

    # Structured HR report routes.
    if any(
        term in q
        for term in (
            "bench",
            "on bench",
            "boşta",
        )
    ):
        return RouteDecision(
            route_type=RouteType.BENCH,
            confidence=0.99,
        )

    if "consultant tracker" in q:
        return RouteDecision(
            route_type=(
                RouteType.CONSULTANT_TRACKER
            ),
            confidence=0.99,
        )

    if any(
        term in q
        for term in (
            "partial assignment",
            "partial assignments",
            "partly assigned",
            "partially assigned",
        )
    ):
        return RouteDecision(
            route_type=(
                RouteType.PARTIAL_ASSIGNMENTS
            ),
            confidence=0.98,
        )

    if any(
        term in q
        for term in (
            "utilisation detailed",
            "detailed utilisation",
            "utilization detailed",
            "detailed utilization",
        )
    ):
        return RouteDecision(
            route_type=(
                RouteType.UTILISATION_DETAILED
            ),
            confidence=0.98,
        )

    if any(
        term in q
        for term in (
            "utilisation",
            "utilization",
        )
    ):
        return RouteDecision(
            route_type=RouteType.UTILISATION,
            confidence=0.97,
        )

    if any(
        term in q
        for term in (
            "project tracker",
            "show projects",
            "list projects",
            "client assignments",
        )
    ):
        return RouteDecision(
            route_type=RouteType.PROJECT_TRACKER,
            confidence=0.90,
        )

    # Generic skill questions that do not contain
    # an explicit person term.
    if (
        any(
            term in q
            for term in (
                "skill",
                "skills",
                "technology",
                "technologies",
                "qualified in",
                "certified in",
            )
        )
        or re.search(
            r"\bhas\s+.+?\s+experience\b",
            q,
        )
        or re.search(
            r"\bhave\s+.+?\s+experience\b",
            q,
        )
    ):
        return RouteDecision(
            route_type=RouteType.SKILL_LOOKUP,
            confidence=0.88,
            extracted_filters=extracted_filters,
        )

    # Individual consultant profile or
    # career-summary questions.
    if _contains_any(
        q,
        PROFILE_TERMS,
    ):
        return RouteDecision(
            route_type=RouteType.PROFILE_SEARCH,
            confidence=0.93,
            extracted_filters=extracted_filters,
        )

    # Document and policy search.
    if any(
        term in q
        for term in (
            "policy",
            "document",
            "pdf",
            "handbook",
            "guideline",
            "procedure",
        )
    ):
        return RouteDecision(
            route_type=RouteType.DOCUMENT_SEARCH,
            confidence=0.95,
            extracted_filters=extracted_filters,
        )

    return RouteDecision(
        route_type=RouteType.UNKNOWN,
        confidence=0.25,
        extracted_filters=extracted_filters,
    )