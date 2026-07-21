"""Individual report viewer."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from ui.layout import render_page_heading
from ui.report_catalog import find_report_file
from ui.report_catalog import get_report
from ui.report_grid import load_parquet_report
from ui.report_grid import render_report_grid


def render() -> None:
    """Render one selected report."""

    report_key = str(
        st.query_params.get("report", "")
    ).strip()

    report = get_report(report_key)

    if report is None:
        render_page_heading(
            title="Report not found",
            description=(
                "The requested report is not registered "
                "in the platform."
            ),
        )

        st.error(
            "Open the Reports page and select one "
            "of the available reports."
        )
        return

    report_path = find_report_file(
        report.filename
    )

    render_page_heading(
        title=report.title,
        description=report.description,
    )

    if report_path is None:
        st.error(
            f"Could not find `{report.filename}` "
            "in the report output directories."
        )
        return

    modified_at = datetime.fromtimestamp(
        report_path.stat().st_mtime
    ).strftime("%d %b %Y, %H:%M")

    st.caption(
        f"Last updated: {modified_at}"
    )

    try:
        with st.spinner(
            f"Loading {report.title}..."
        ):
            dataframe = load_parquet_report(
                path_string=str(report_path),
                modified_timestamp=(
                    report_path.stat().st_mtime
                ),
            )

    except Exception as error:
        st.error(
            f"The report could not be loaded: {error}"
        )
        return

    render_report_grid(
        dataframe=dataframe,
        report_key=report.key,
    )