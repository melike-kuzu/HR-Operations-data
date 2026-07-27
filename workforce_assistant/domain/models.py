from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RouteType(str, Enum):
    BENCH = "bench"
    CONSULTANT_TRACKER = "consultant_tracker"
    PROJECT_TRACKER = "project_tracker"
    UTILISATION = "utilisation"
    UTILISATION_DETAILED = "utilisation_detailed"
    PARTIAL_ASSIGNMENTS = "partial_assignments"
    SKILL_LOOKUP = "skill_lookup"
    PROFILE_SEARCH = "profile_search"
    DOCUMENT_SEARCH = "document_search"
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RouteDecision:
    route_type: RouteType
    confidence: float
    extracted_filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    answer: str
    route: RouteType
    tables: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
