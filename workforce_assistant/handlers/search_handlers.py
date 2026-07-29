from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
import re
import unicodedata

import pandas as pd

from workforce_assistant.domain.models import (
    ChatResponse,
    RouteType,
)
from workforce_assistant.llm.azure_openai_chat_model import (
    AzureOpenAIChatModel,
)
from workforce_assistant.llm.chat_model import ChatModel
from workforce_assistant.repositories.parquet_repository import (
    load_report,
)
from workforce_assistant.repositories.search_repository import (
    SearchDocument,
    SearchRepository,
)


AVAILABLE_STATUSES = {
    "BENCH",
    "PARTLY_BOOKED",
}


def handle_search_route(
    question: str,
    route_type: RouteType,
    search_repository: SearchRepository,
    *,
    extracted_filters: dict | None = None,
    chat_model: ChatModel | None = None,
) -> ChatResponse:
    extracted_filters = extracted_filters or {}

    source_filter = {
        RouteType.PROFILE_SEARCH: {
            "source_type": "profile_generator",
        },
        RouteType.DOCUMENT_SEARCH: None,
    }.get(route_type)

    # Use the extracted technology as the search query where possible.
    # This prevents availability wording from weakening Azure Search.
    search_query = str(
        extracted_filters.get(
            "skill_query",
            question,
        )
    ).strip()

    documents = search_repository.search(
        search_query,
        top_k=30,
        filters=source_filter,
    )

    if not documents:
        return ChatResponse(
            answer=(
                "No relevant indexed content was found."
            ),
            route=route_type,
            metadata={
                "search_result_count": 0,
                "unique_consultant_count": 0,
                "filtered_consultant_count": 0,
                "extracted_filters": extracted_filters,
            },
        )

    unique_documents = _deduplicate_documents(
        documents
    )

    filtered_documents = _apply_structured_filters(
        unique_documents,
        extracted_filters,
    )

    if not filtered_documents:
        return ChatResponse(
            answer=(
                "I found consultants matching the requested "
                "skill, but none matched the requested "
                "availability or workforce filters."
            ),
            route=route_type,
            metadata={
                "search_result_count": len(documents),
                "unique_consultant_count": len(
                    unique_documents
                ),
                "filtered_consultant_count": 0,
                "source_type_filter": (
                    source_filter or {}
                ),
                "extracted_filters": extracted_filters,
                "llm_provider": "not_called",
            },
        )

    context = [
        _document_to_context(document)
        for document in filtered_documents
    ]

    # Add verified workforce information to the context.
    structured_context = _build_structured_context(
        filtered_documents,
        extracted_filters,
    )

    context.extend(structured_context)

    model = chat_model or AzureOpenAIChatModel()

    answer = model.generate(
        question=question,
        context=context,
    )

    return ChatResponse(
        answer=answer,
        route=route_type,
        sources=[
            {
                "id": document.id,
                "title": document.title,
                "source_file": document.source_file,
                "consultant_name":
                    document.consultant_name,
                "page_number": document.page_number,
                "score": document.score,
            }
            for document in filtered_documents
        ],
        metadata={
            "search_result_count": len(documents),
            "unique_consultant_count": len(
                unique_documents
            ),
            "filtered_consultant_count": len(
                filtered_documents
            ),
            "source_type_filter": (
                source_filter or {}
            ),
            "extracted_filters": extracted_filters,
            "structured_filter_applied": bool(
                _has_structured_filters(
                    extracted_filters
                )
            ),
            "llm_provider": "azure_openai",
        },
    )


def _has_structured_filters(
    extracted_filters: dict,
) -> bool:
    return any(
        key in extracted_filters
        for key in (
            "availability",
            "active_projects",
            "group",
        )
    )


def _apply_structured_filters(
    documents: list[SearchDocument],
    extracted_filters: dict,
) -> list[SearchDocument]:
    if not _has_structured_filters(
        extracted_filters
    ):
        return documents

    tracker = load_report(
        "consultant_tracker"
    )

    if tracker.empty:
        return []

    name_column = _find_column(
        tracker,
        (
            "Consultant_Name",
            "Consultant Name",
            "EmployeeName",
            "Employee Name",
            "Resource_Name",
            "Resource Name",
        ),
    )

    if name_column is None:
        raise ValueError(
            "Consultant tracker does not contain a "
            "recognised consultant-name column."
        )

    filtered_tracker = tracker.copy()

    availability_filter = (
        extracted_filters.get(
            "availability"
        )
    )

    if availability_filter == "next_month":
        filtered_tracker = (
            _filter_available_next_month(
                filtered_tracker
            )
        )

    elif availability_filter == "bench":
        filtered_tracker = (
            _filter_current_bench(
                filtered_tracker
            )
        )

    active_projects_filter = (
        extracted_filters.get(
            "active_projects"
        )
    )

    if active_projects_filter:
        filtered_tracker = (
            _filter_active_projects(
                filtered_tracker,
                active_projects_filter,
            )
        )

    group_filter = extracted_filters.get(
        "group"
    )

    if group_filter:
        filtered_tracker = _filter_group(
            filtered_tracker,
            str(group_filter),
        )

    allowed_names = {
        _normalise_name(value)
        for value in filtered_tracker[
            name_column
        ].dropna()
        if _normalise_name(value)
    }

    return [
        document
        for document in documents
        if _normalise_name(
            document.consultant_name
        )
        in allowed_names
    ]


def _filter_available_next_month(
    tracker: pd.DataFrame,
) -> pd.DataFrame:
    today = date.today()

    if today.month == 12:
        next_month_start = date(
            today.year + 1,
            1,
            1,
        )
    else:
        next_month_start = date(
            today.year,
            today.month + 1,
            1,
        )

    if next_month_start.month == 12:
        month_after_start = date(
            next_month_start.year + 1,
            1,
            1,
        )
    else:
        month_after_start = date(
            next_month_start.year,
            next_month_start.month + 1,
            1,
        )

    status_columns = _status_columns_between(
        tracker,
        start_date=next_month_start,
        end_date=month_after_start,
    )

    if not status_columns:
        return tracker.iloc[0:0].copy()

    status_frame = (
        tracker[status_columns]
        .astype("string")
        .apply(
            lambda column: (
                column
                .str.strip()
                .str.upper()
            )
        )
    )

    # A consultant is treated as available next month
    # when at least one next-month week is BENCH or
    # PARTLY_BOOKED.
    availability_mask = status_frame.isin(
        AVAILABLE_STATUSES
    ).any(axis=1)

    return tracker.loc[
        availability_mask
    ].copy()


def _filter_current_bench(
    tracker: pd.DataFrame,
) -> pd.DataFrame:
    dated_status_columns = (
        _get_dated_status_columns(
            tracker
        )
    )

    if not dated_status_columns:
        return tracker.iloc[0:0].copy()

    today = date.today()

    past_or_current_columns = [
        item
        for item in dated_status_columns
        if item[0] <= today
    ]

    if past_or_current_columns:
        _, current_column = max(
            past_or_current_columns,
            key=lambda item: item[0],
        )
    else:
        _, current_column = min(
            dated_status_columns,
            key=lambda item: item[0],
        )

    values = (
        tracker[current_column]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return tracker.loc[
        values.eq("BENCH")
    ].copy()


def _filter_active_projects(
    tracker: pd.DataFrame,
    filter_definition: object,
) -> pd.DataFrame:
    active_projects_column = _find_column(
        tracker,
        (
            "Active_Projects",
            "Active Projects",
            "ActiveProjects",
        ),
    )

    if active_projects_column is None:
        return tracker.iloc[0:0].copy()

    if not isinstance(
        filter_definition,
        dict,
    ):
        return tracker

    operator = filter_definition.get(
        "operator"
    )
    value = filter_definition.get(
        "value"
    )

    if value is None:
        return tracker

    numeric_values = pd.to_numeric(
        tracker[active_projects_column],
        errors="coerce",
    )

    numeric_filter_value = float(value)

    if operator == "lt":
        mask = numeric_values.lt(
            numeric_filter_value
        )
    elif operator == "lte":
        mask = numeric_values.le(
            numeric_filter_value
        )
    elif operator == "gt":
        mask = numeric_values.gt(
            numeric_filter_value
        )
    elif operator == "gte":
        mask = numeric_values.ge(
            numeric_filter_value
        )
    elif operator == "eq":
        mask = numeric_values.eq(
            numeric_filter_value
        )
    else:
        return tracker

    return tracker.loc[
        mask.fillna(False)
    ].copy()


def _filter_group(
    tracker: pd.DataFrame,
    requested_group: str,
) -> pd.DataFrame:
    group_column = _find_column(
        tracker,
        (
            "Group",
            "Group_Name",
            "Group Name",
        ),
    )

    if group_column is None:
        return tracker.iloc[0:0].copy()

    requested_value = (
        requested_group
        .strip()
        .lower()
    )

    group_values = (
        tracker[group_column]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    return tracker.loc[
        group_values.str.contains(
            re.escape(requested_value),
            regex=True,
            na=False,
        )
    ].copy()


def _build_structured_context(
    documents: list[SearchDocument],
    extracted_filters: dict,
) -> list[str]:
    if not _has_structured_filters(
        extracted_filters
    ):
        return []

    tracker = load_report(
        "consultant_tracker"
    )

    name_column = _find_column(
        tracker,
        (
            "Consultant_Name",
            "Consultant Name",
            "EmployeeName",
            "Employee Name",
            "Resource_Name",
            "Resource Name",
        ),
    )

    if name_column is None:
        return []

    requested_names = {
        _normalise_name(
            document.consultant_name
        )
        for document in documents
        if document.consultant_name
    }

    matched_rows = tracker.loc[
        tracker[name_column]
        .map(_normalise_name)
        .isin(requested_names)
    ].copy()

    group_column = _find_column(
        matched_rows,
        (
            "Group",
            "Group_Name",
            "Group Name",
        ),
    )

    active_projects_column = _find_column(
        matched_rows,
        (
            "Active_Projects",
            "Active Projects",
            "ActiveProjects",
        ),
    )

    contexts: list[str] = []

    for _, row in matched_rows.iterrows():
        consultant_name = row.get(
            name_column
        )

        parts = [
            (
                "Verified workforce information for "
                f"{consultant_name}:"
            )
        ]

        if group_column:
            parts.append(
                f"Group: {row.get(group_column)}"
            )

        if active_projects_column:
            parts.append(
                "Active projects: "
                f"{row.get(active_projects_column)}"
            )

        availability = (
            extracted_filters.get(
                "availability"
            )
        )

        if availability == "next_month":
            parts.append(
                "Availability filter verified: "
                "the consultant has at least one "
                "BENCH or PARTLY_BOOKED week "
                "during next month."
            )

        elif availability == "bench":
            parts.append(
                "Availability filter verified: "
                "the consultant is currently BENCH."
            )

        contexts.append(
            "\n".join(parts)
        )

    return contexts


def _status_columns_between(
    dataframe: pd.DataFrame,
    *,
    start_date: date,
    end_date: date,
) -> list[str]:
    return [
        column_name
        for column_date, column_name
        in _get_dated_status_columns(
            dataframe
        )
        if (
            start_date
            <= column_date
            < end_date
        )
    ]


def _get_dated_status_columns(
    dataframe: pd.DataFrame,
) -> list[tuple[date, str]]:
    dated_columns: list[
        tuple[date, str]
    ] = []

    for column in dataframe.columns:
        column_name = str(column)

        if not column_name.endswith(
            "__STATUS"
        ):
            continue

        date_text = column_name.removesuffix(
            "__STATUS"
        )

        try:
            column_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            continue

        dated_columns.append(
            (
                column_date,
                column_name,
            )
        )

    return sorted(
        dated_columns,
        key=lambda item: item[0],
    )


def _find_column(
    dataframe: pd.DataFrame,
    candidates: tuple[str, ...],
) -> str | None:
    columns_by_normalised_name = {
        _normalise_column_name(column):
            str(column)
        for column in dataframe.columns
    }

    for candidate in candidates:
        match = columns_by_normalised_name.get(
            _normalise_column_name(
                candidate
            )
        )

        if match:
            return match

    return None


def _normalise_column_name(
    value: object,
) -> str:
    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower(),
    )


def _normalise_name(
    value: object,
) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    text = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    text = text.lower().strip()

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text,
    )


def _deduplicate_documents(
    documents: list[SearchDocument],
) -> list[SearchDocument]:
    unique: OrderedDict[
        str,
        SearchDocument,
    ] = OrderedDict()

    for document in documents:
        consultant_id = document.metadata.get(
            "consultant_id"
        )

        consultant_name = (
            document.consultant_name or ""
        ).strip().lower()

        if consultant_id:
            key = f"id:{consultant_id}"
        elif consultant_name:
            key = f"name:{consultant_name}"
        else:
            key = f"document:{document.id}"

        existing = unique.get(key)

        if existing is None:
            unique[key] = document
            continue

        existing_score = existing.score or 0.0
        new_score = document.score or 0.0

        if new_score > existing_score:
            unique[key] = document

    return list(
        unique.values()
    )


def _document_to_context(
    document: SearchDocument,
) -> str:
    parts = []

    if document.consultant_name:
        parts.append(
            f"Consultant: "
            f"{document.consultant_name}"
        )

    consultant_id = document.metadata.get(
        "consultant_id"
    )

    if consultant_id:
        parts.append(
            f"Consultant ID: {consultant_id}"
        )

    if document.title:
        parts.append(
            f"Title: {document.title}"
        )

    if document.source_file:
        parts.append(
            f"Source file: "
            f"{document.source_file}"
        )

    sheet_name = document.metadata.get(
        "sheet_name"
    )

    if sheet_name:
        parts.append(
            f"Sheet: {sheet_name}"
        )

    parts.append(
        f"Content:\n{document.content}"
    )

    return "\n".join(parts)