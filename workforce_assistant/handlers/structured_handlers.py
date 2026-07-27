from __future__ import annotations

import pandas as pd

from workforce_assistant.domain.models import ChatResponse, RouteType
from workforce_assistant.repositories.parquet_repository import load_report


REPORT_BY_ROUTE = {
    RouteType.BENCH: "bench_status",
    RouteType.CONSULTANT_TRACKER: "consultant_tracker",
    RouteType.PROJECT_TRACKER: "project_tracker",
    RouteType.UTILISATION: "utilisation",
    RouteType.UTILISATION_DETAILED: "utilisation_detailed",
    RouteType.PARTIAL_ASSIGNMENTS: "partial_assignments",
}


def handle_structured_route(
    route_type: RouteType,
    question: str,
) -> ChatResponse:
    report_name = REPORT_BY_ROUTE[route_type]
    dataframe = load_report(report_name)

    return ChatResponse(
    answer=(
        f"Loaded {report_name.replace('_', ' ')} "
        f"with {len(dataframe)} row(s)."
    ),
    route=route_type,
    tables={
        report_name: dataframe,
    },
    metadata={
        "question": question,
        "report_name": report_name,
        "filters": {},
        "replay_supported": True,
    },
)



def handle_skill_lookup(question: str) -> ChatResponse:
    technologies = load_report("technologies")

    stop_words = {
        "who",
        "knows",
        "know",
        "has",
        "have",
        "with",
        "find",
        "consultant",
        "consultants",
        "employee",
        "employees",
        "show",
        "me",
        "someone",
        "experience",
        "experienced",
        "skill",
        "skills",
    }

    query_terms = [
        token.strip("?,.!:;()[]{}").lower()
        for token in question.split()
        if (
            len(token.strip("?,.!:;()[]{}")) > 2
            and token.strip("?,.!:;()[]{}").lower()
            not in stop_words
        )
    ]

    if not query_terms:
        return ChatResponse(
            answer=(
                "Please specify a technology, "
                "for example Azure, AWS, Python or Databricks."
            ),
            route=RouteType.SKILL_LOOKUP,
            tables={},
        )

    technology_values = (
        technologies["TechnologyName"]
        .astype("string")
        .str.lower()
        .fillna("")
    )

    technology_mask = pd.Series(
        False,
        index=technologies.index,
    )

    for term in query_terms:
        technology_mask |= technology_values.str.contains(
            term,
            regex=False,
            na=False,
        )

    matches = technologies.loc[
        technology_mask
    ].copy()

    # Remove employees explicitly marked as having no knowledge.
    if "Level.1" in matches.columns:
        knowledge_level = (
            matches["Level.1"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        matches = matches.loc[
            knowledge_level.ne("no knowledge")
            & knowledge_level.notna()
        ].copy()

    # Prefer current employees only.
    if "Status" in matches.columns:
        current_status = (
            matches["Status"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        matches = matches.loc[
            current_status.eq("current")
        ].copy()

    output_columns = [
        column
        for column in [
            "EmployeeName",
            "Level",
            "TechnologyName",
            "Vendor",
            "Priority",
            "Level.1",
            "LevelShort (stars)",
            "Type",
            "Manager",
            "Office",
            "UpdateDate",
        ]
        if column in matches.columns
    ]

    matches = matches[
        output_columns
    ].drop_duplicates()

    sort_columns = [
        column
        for column in [
            "EmployeeName",
            "TechnologyName",
        ]
        if column in matches.columns
    ]

    if sort_columns:
        matches = matches.sort_values(
            sort_columns
        )

    employee_count = (
        matches["EmployeeName"].nunique()
        if "EmployeeName" in matches.columns
        else len(matches)
    )

    searched_terms = ", ".join(query_terms)

    return ChatResponse(
        answer=(
            f"Found {employee_count} current employee(s) "
            f"with recorded knowledge matching "
            f"'{searched_terms}'."
        ),
        route=RouteType.SKILL_LOOKUP,
        tables={
            "technology_matches": matches
        },
        sources=[
            "technologies"
        ],
        metadata={
            "report_name": "technologies",
            "filters": {
                "search_terms": query_terms,
                "current_employees_only": True,
                "exclude_no_knowledge": True,
            },
            "replay_supported": True,
            "search_terms": query_terms,
            "employee_count": employee_count,
            "match_count": len(matches),
        },
    )
