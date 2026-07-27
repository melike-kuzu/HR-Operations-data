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
    normalised = re.sub(r"\s+", " ", normalised)
    return normalised


def _contains_any(
    question: str,
    terms: tuple[str, ...],
) -> bool:
    return any(term in question for term in terms)


def _is_skill_lookup(question: str) -> bool:
    has_person_intent = _contains_any(
        question,
        PERSON_LOOKUP_TERMS,
    )

    has_skill_intent = _contains_any(
        question,
        SKILL_INTENT_TERMS,
    )

    return has_person_intent and has_skill_intent


def route_question(question: str) -> RouteDecision:
    q = _normalise_question(question)

    # Structured HR report routes
    if any(
        term in q
        for term in (
            "bench",
            "on bench",
            "boşta",
        )
    ):
        return RouteDecision(
            RouteType.BENCH,
            0.99,
        )

    if "consultant tracker" in q:
        return RouteDecision(
            RouteType.CONSULTANT_TRACKER,
            0.99,
        )

    if any(
        term in q
        for term in (
            "partial assignment",
            "partly assigned",
            "partially assigned",
        )
    ):
        return RouteDecision(
            RouteType.PARTIAL_ASSIGNMENTS,
            0.98,
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
            RouteType.UTILISATION_DETAILED,
            0.98,
        )

    if any(
        term in q
        for term in (
            "utilisation",
            "utilization",
        )
    ):
        return RouteDecision(
            RouteType.UTILISATION,
            0.97,
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
            RouteType.PROJECT_TRACKER,
            0.90,
        )

    # Person + technology/skill question.
    # This must come before profile/document search.
    if _is_skill_lookup(q):
        return RouteDecision(
            RouteType.SKILL_LOOKUP,
            0.96,
        )

    # Generic skill questions without an explicit person word.
    if any(
        term in q
        for term in (
            "skill",
            "skills",
            "technology",
            "technologies",
            "qualified in",
            "certified in",
        )
    ):
        return RouteDecision(
            RouteType.SKILL_LOOKUP,
            0.88,
        )

    # Individual profile or career-summary questions.
    if _contains_any(q, PROFILE_TERMS):
        return RouteDecision(
            RouteType.PROFILE_SEARCH,
            0.93,
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
            RouteType.DOCUMENT_SEARCH,
            0.95,
        )

    return RouteDecision(
        RouteType.UNKNOWN,
        0.25,
    )