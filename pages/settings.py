"""Settings page."""

from __future__ import annotations

import streamlit as st

from ui.layout import render_page_heading


def render() -> None:
    render_page_heading(
        title="Settings",
        description=(
            "Application preferences and reporting configuration."
        ),
    )

    st.markdown(
        """
        <div class="empty-panel">
            <h3>Settings</h3>
            <p>
                Configuration controls will be added after the reports
                workflow is complete.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )