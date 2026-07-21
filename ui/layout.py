"""Shared layout components."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

import streamlit as st

from ui.styles import apply_global_styles


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.svg"


def _svg_as_data_uri(path: Path) -> str | None:
    """Convert an SVG file into a browser-safe data URI."""

    if not path.is_file():
        return None

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def configure_page() -> None:
    """Configure the Streamlit application."""

    st.set_page_config(
        page_title="HR Decision Support Platform",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_global_styles()


def render_top_header() -> None:
    """Render the company logo and platform title."""

    logo_uri = _svg_as_data_uri(LOGO_PATH)

    if logo_uri is not None:
        logo_html = (
            f'<img class="platform-header__logo" '
            f'src="{logo_uri}" alt="Company logo">'
        )
    else:
        logo_html = (
            '<div class="platform-header__logo-fallback">'
            "COMPANY"
            "</div>"
        )

    header_html = (
        '<div class="platform-header">'
        '<div class="platform-header__left">'
        f"{logo_html}"
        '<div class="platform-header__divider"></div>'
        '<div class="platform-header__content">'
        '<div class="platform-header__title">'
        "HR Decision Support Platform"
        "</div>"
        '<div class="platform-header__subtitle">'
        "Resource Planning • Workforce Analytics • AI Decision Support"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )

    st.html(header_html)


def render_page_heading(
    title: str,
    description: str,
) -> None:
    """Render a page title and supporting description."""

    heading_html = (
        '<div class="page-heading">'
        f"<h1>{title}</h1>"
        f"<p>{description}</p>"
        "</div>"
    )

    st.html(heading_html)


def render_sidebar(
    latest_data_date: datetime | None = None,
) -> None:
    """Render sidebar context and latest dataset information."""

    with st.sidebar:
        st.html(
            """
            <div class="sidebar-workspace">
                <div class="sidebar-workspace__label">
                    Workspace
                </div>
                <div class="sidebar-workspace__title">
                    HR Decision Support
                </div>
            </div>
            """
        )

        if latest_data_date is None:
            latest_date_text = "Not available"
            latest_time_text = "Dataset date not detected"
        else:
            latest_date_text = latest_data_date.strftime("%d %b %Y")
            latest_time_text = latest_data_date.strftime("%H:%M")

        st.html(
            f"""
            <div class="sidebar-data-info">
                <div class="sidebar-data-info__label">
                    Latest data
                </div>
                <div class="sidebar-data-info__value">
                    {latest_date_text}
                </div>
                <div class="sidebar-data-info__caption">
                    Last updated at {latest_time_text}
                </div>
            </div>
            """
        )