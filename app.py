"""Entry point for the HR Decision Support Platform."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from pages import admin_audit
from pages import chatbot_page
from pages import dashboard
from pages import report_view
from pages import reports
from pages import settings
from ui.layout import configure_page
from ui.layout import render_sidebar
from ui.layout import render_top_header

from workforce_assistant.config.logging_config import configure_logging


PROJECT_ROOT = Path(__file__).resolve().parent

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}


@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def get_latest_dataset_time() -> datetime | None:
    """
    Return the latest modification time among generated parquet reports.

    The filesystem result is cached for 60 seconds so Streamlit does not
    scan the complete project directory on every page navigation.
    """

    latest_timestamp: float | None = None

    for path in PROJECT_ROOT.rglob("*.parquet"):
        if not path.is_file():
            continue

        if any(
            directory_name in path.parts
            for directory_name in IGNORED_DIRECTORIES
        ):
            continue

        current_timestamp = path.stat().st_mtime

        if (
            latest_timestamp is None
            or current_timestamp > latest_timestamp
        ):
            latest_timestamp = current_timestamp

    if latest_timestamp is None:
        return None

    return datetime.fromtimestamp(
        latest_timestamp
    )


def create_navigation():
    """Create the application navigation."""

    dashboard_page = st.Page(
        dashboard.render,
        title="Home",
        icon=":material/home:",
        url_path="dashboard",
        default=True,
    )

    reports_page = st.Page(
        reports.render,
        title="Reports",
        icon=":material/table_view:",
        url_path="reports",
    )

    assistant_page = st.Page(
        chatbot_page.render,
        title="AI Workforce Assistant",
        icon=":material/smart_toy:",
        url_path="hr-assistant",
    )

    settings_page = st.Page(
        settings.render,
        title="Settings",
        icon=":material/settings:",
        url_path="settings",
    )

    admin_audit_page = st.Page(
    admin_audit.render,
    title="Admin / Audit",
    icon=":material/admin_panel_settings:",
    url_path="admin-audit",
)

    report_viewer_page = st.Page(
        report_view.render,
        title="Report Viewer",
        url_path="report-view",
        visibility="hidden",
    )

    return st.navigation(
        [
            dashboard_page,
            reports_page,
            assistant_page,
            admin_audit_page,
            settings_page,
            report_viewer_page,
        ],
        position="sidebar",
    )


def main() -> None:
    """Run the HR Decision Support Platform."""
    configure_logging()
    configure_page()
    

    navigation = create_navigation()

    latest_dataset_time = (
        get_latest_dataset_time()
    )

    render_sidebar(
        latest_data_date=latest_dataset_time,
    )

    render_top_header()

    navigation.run()


if __name__ == "__main__":
    main()