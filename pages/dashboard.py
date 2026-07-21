"""Dashboard page for the HR Decision Support Platform."""

from __future__ import annotations

import getpass

import streamlit as st

from ui.layout import render_page_heading


def _get_display_name() -> str:
    """
    Return a temporary local display name.

    This can later be replaced by the authenticated Azure user name.
    """

    try:
        username = getpass.getuser().strip()
    except Exception:
        return "User"

    if not username:
        return "User"

    cleaned_name = username.replace(".", " ").replace("_", " ").strip()

    first_name = cleaned_name.split()[0]

    return first_name.title()

    


def _render_metric_card(
    label: str,
    value: str,
    caption: str,
) -> None:
    """Render a dashboard metric card."""

    st.html(
        f"""
        <div class="metric-card">
            <div class="metric-card__accent"></div>
            <div class="metric-card__label">{label}</div>
            <div class="metric-card__value">{value}</div>
            <div class="metric-card__caption">{caption}</div>
        </div>
        """
    )


def render() -> None:
    """Render the dashboard."""

    display_name = _get_display_name()

    render_page_heading(
        title=f"Welcome {display_name} !",
        description=(
            "Access workforce reports, planning insights "
            "and AI decision support."
        ),
    )

    metric_columns = st.columns(2)

    with metric_columns[0]:
        _render_metric_card(
            label="Consultants",
            value="210",
            caption="Active consultant records",
        )

    with metric_columns[1]:
        _render_metric_card(
            label="Available reports",
            value="6",
            caption="Operational report outputs",
        )

    st.html('<div class="section-title">Workspace overview</div>')

    overview_columns = st.columns([1.6, 1])

    with overview_columns[0]:
        st.html(
            """
            <div class="empty-panel" style="text-align: left;">
                <h3>Workforce reporting</h3>
                <p style="margin-left: 0;">
                    Review consultant schedules, project assignments,
                    utilisation, bench status and partial allocations.
                    Reports retain their original columns, ordering and
                    business logic.
                </p>
            </div>
            """
        )

    with overview_columns[1]:
        st.html(
            """
            <div class="empty-panel" style="text-align: left;">
                <h3>HR Assistant</h3>
                <p style="margin-left: 0;">
                    Use AI-assisted access to approved workforce reports
                    and HR reference information.
                </p>
            </div>
            """
        )