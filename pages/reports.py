"""Reports landing page."""

from __future__ import annotations

from html import escape

import streamlit as st

from ui.layout import render_page_heading
from ui.report_catalog import REPORTS
from ui.report_catalog import find_report_file


@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def _report_file_exists(
    filename: str,
) -> bool:
    """
    Check whether a report output exists.

    The result is cached so the application does not repeatedly scan
    report directories every time the Reports page reruns.
    """

    return (
        find_report_file(filename)
        is not None
    )


def _render_report_card(
    title: str,
    description: str,
    symbol: str,
    report_key: str,
    is_available: bool,
) -> None:
    """Render a report card."""

    status_label = (
        "Available"
        if is_available
        else "File not found"
    )

    status_class = (
        "available"
        if is_available
        else "unavailable"
    )

    report_url = (
        f"/report-view?report={report_key}"
    )

    card_html = (
        f'<a class="report-card-link" '
        f'href="{escape(report_url)}" '
        f'target="_blank" '
        f'rel="noopener noreferrer">'
        '<article class="report-card">'
        '<div class="report-card__top">'
        f'<div class="report-card__icon">'
        f'{escape(symbol)}'
        '</div>'
        '<div class="report-card__external">'
        '↗'
        '</div>'
        '</div>'
        f'<div class="report-card__title">'
        f'{escape(title)}'
        '</div>'
        f'<div class="report-card__description">'
        f'{escape(description)}'
        '</div>'
        '<div class="report-card__footer">'
        f'<span class="report-card__status '
        f'report-card__status--{status_class}">'
        f'{escape(status_label)}'
        '</span>'
        '<span>Open report</span>'
        '</div>'
        '</article>'
        '</a>'
    )

    st.html(card_html)


def render() -> None:
    """Render the report catalogue."""

    render_page_heading(
        title="Reports",
        description=(
            "Open official workforce and resource-planning reports. "
            "Each report opens in a separate browser tab so multiple "
            "reports can be reviewed at the same time."
        ),
    )

    report_availability = {
        report.filename: _report_file_exists(
            report.filename
        )
        for report in REPORTS
    }

    for row_start in range(
        0,
        len(REPORTS),
        3,
    ):
        row_reports = REPORTS[
            row_start : row_start + 3
        ]

        columns = st.columns(3)

        for column, report in zip(
            columns,
            row_reports,
        ):
            with column:
                _render_report_card(
                    title=report.title,
                    description=report.description,
                    symbol=report.symbol,
                    report_key=report.key,
                    is_available=(
                        report_availability[
                            report.filename
                        ]
                    ),
                )