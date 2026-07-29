from __future__ import annotations

import pandas as pd
import streamlit as st

from workforce_assistant.repositories.audit_repository import (
    load_audit_events,
)


def _render_summary_metrics(
    audit_events: pd.DataFrame,
) -> None:
    completed_events = audit_events.loc[
        audit_events["event_type"].eq(
            "chat_request_completed"
        )
    ].copy()

    failed_events = audit_events.loc[
        audit_events["event_type"].eq(
            "chat_request_failed"
        )
    ].copy()

    total_requests = len(
        completed_events
    ) + len(
        failed_events
    )

    successful_requests = len(
        completed_events
    )

    failed_requests = len(
        failed_events
    )

    response_times = pd.to_numeric(
        completed_events["response_time_ms"],
        errors="coerce",
    )

    average_response_time = (
        response_times.mean()
        if not response_times.empty
        else 0
    )

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Total requests",
        total_requests,
    )

    metric_columns[1].metric(
        "Successful",
        successful_requests,
    )

    metric_columns[2].metric(
        "Failed",
        failed_requests,
    )

    metric_columns[3].metric(
        "Average response time",
        (
            f"{average_response_time:.0f} ms"
            if pd.notna(average_response_time)
            else "0 ms"
        ),
    )


def _render_route_summary(
    audit_events: pd.DataFrame,
) -> None:
    completed_events = audit_events.loc[
        audit_events["event_type"].eq(
            "chat_request_completed"
        )
    ].copy()

    if completed_events.empty:
        st.info(
            "No completed chatbot requests are available."
        )
        return

    route_summary = (
        completed_events.groupby(
            "route",
            dropna=False,
        )
        .size()
        .reset_index(
            name="request_count"
        )
        .sort_values(
            "request_count",
            ascending=False,
        )
    )

    st.subheader(
        "Requests by route"
    )

    st.dataframe(
        route_summary,
        use_container_width=True,
        hide_index=True,
    )


def _render_event_table(
    audit_events: pd.DataFrame,
) -> None:
    st.subheader(
        "Recent user requests"
    )

    request_events = audit_events.loc[
        audit_events["event_type"].isin(
            [
                "chat_request_completed",
                "chat_request_failed",
            ]
        )
    ].copy()

    if request_events.empty:
        st.info(
            "No completed user requests are available."
        )
        return

    request_events["User"] = (
        request_events["user_id"]
        .fillna("Unknown user")
    )

    request_events["Question"] = (
        request_events["question"]
        .fillna("Question was not recorded")
    )

    request_events["Route"] = (
        request_events["route"]
        .fillna("unknown")
    )

    response_time = pd.to_numeric(
        request_events["response_time_ms"],
        errors="coerce",
    )

    request_events["Response Time"] = (
        response_time
        .round(0)
        .astype("Int64")
        .astype("string")
        .fillna("-")
        + " ms"
    )

    request_events["Success"] = (
        request_events["success"]
        .map(
            {
                True: "✅",
                False: "❌",
            }
        )
        .fillna("❌")
    )

    display_table = request_events[
        [
            "User",
            "Question",
            "Route",
            "Response Time",
            "Success",
        ]
    ]

    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "User": st.column_config.TextColumn(
                "User",
                width="medium",
            ),
            "Question": st.column_config.TextColumn(
                "Question",
                width="large",
            ),
            "Route": st.column_config.TextColumn(
                "Route",
                width="medium",
            ),
            "Response Time": st.column_config.TextColumn(
                "Response Time",
                width="small",
            ),
            "Success": st.column_config.TextColumn(
                "Success",
                width="small",
            ),
        },
    )

def render() -> None:
    """Render the chatbot audit administration page."""

    st.title(
        "Admin / Audit"
    )

    st.caption(
        "Monitor chatbot requests, routes, "
        "response times and failures."
    )

    audit_events = load_audit_events(
        limit=1000,
    )

    if audit_events.empty:
        st.warning(
            "No chatbot audit events were found. "
            "Make sure file logging is enabled and "
            "ask the assistant at least one question."
        )
        return

    _render_summary_metrics(
        audit_events
    )

    st.divider()

    _render_route_summary(
        audit_events
    )

    st.divider()

    _render_event_table(
        audit_events
    )