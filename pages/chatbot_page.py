"""HR Assistant page."""

from __future__ import annotations

import streamlit as st

from ui.layout import render_page_heading


def render() -> None:
    render_page_heading(
        title="HR Assistant",
        description=(
            "Ask controlled questions about workforce reporting and "
            "approved HR reference information."
        ),
    )

    st.markdown(
        """
        <div class="empty-panel">
            <h3>Assistant workspace</h3>
            <p>
                The conversational interface will be connected after the
                reporting interface is complete.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )