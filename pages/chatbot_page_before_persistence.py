"""AI Workforce Assistant page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from workforce_assistant.services.chatbot_service import ask_data_question
from ui.layout import render_page_heading

SUGGESTED_QUESTIONS = (
    "Who knows Azure?",
    "Who is on bench today?",
    "Who becomes available next month?",
    "Find an AWS consultant with banking experience.",
)


def _initialise_chat() -> None:
    if "workforce_messages" not in st.session_state:
        st.session_state.workforce_messages = [{
            "role": "assistant",
            "content": (
                "Hi! I can help you find consultants, review availability, search skills and "
                "experience, and explore workforce and project information."
            ),
            "table": None,
            "sources": [],
        }]


def _reset_chat() -> None:
    st.session_state.pop("workforce_messages", None)
    st.session_state.pop("workforce_pending_question", None)
    st.rerun()


def _render_styles() -> None:
    st.markdown(
        """
        <style>
        .source-chip {
            display: inline-block;
            padding: .22rem .55rem;
            margin: .15rem .25rem .1rem 0;
            border-radius: 999px;
            background: rgba(0,175,193,.11);
            color: #006f79;
            font-size: .75rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_message(message: dict[str, object]) -> None:
    with st.chat_message(str(message["role"])):
        st.markdown(str(message["content"]))

        sources = message.get("sources") or []
        if sources:
            st.markdown(
                "".join(f'<span class="source-chip">{source}</span>' for source in sources),
                unsafe_allow_html=True,
            )

        table = message.get("table")
        if isinstance(table, pd.DataFrame) and not table.empty:
            with st.expander(f"View supporting data ({len(table)} records)", expanded=True):
                st.dataframe(
                    table,
                    use_container_width=True,
                    hide_index=True,
                    height=min(420, 42 + (len(table) * 35)),
                )


def _submit_question(question: str) -> None:
    clean_question = question.strip()

    if not clean_question:
        return

    st.session_state.workforce_messages.append(
        {
            "role": "user",
            "content": clean_question,
            "table": None,
            "sources": [],
        }
    )

    try:
        with st.spinner("Analysing workforce data..."):
            result = ask_data_question(clean_question)

        answer = result.get(
            "answer",
            "The request was processed, but no written answer was returned.",
        )

        sources = result.get("sources", [])

        # Support both the old `table` response and
        # the new `tables` dictionary response.
        table = result.get("table")

        if not isinstance(table, pd.DataFrame):
            tables = result.get("tables", {})

            if isinstance(tables, dict):
                table = next(
                    (
                        value
                        for value in tables.values()
                        if isinstance(value, pd.DataFrame)
                    ),
                    pd.DataFrame(),
                )
            else:
                table = pd.DataFrame()

    except Exception as error:
        answer = f"I could not complete that request: {error}"
        table = pd.DataFrame()
        sources = []

    st.session_state.workforce_messages.append(
        {
            "role": "assistant",
            "content": answer,
            "table": table,
            "sources": sources,
        }
    )


def render() -> None:
    _initialise_chat()
    _render_styles()

    heading_columns = st.columns([5, 1])
    with heading_columns[0]:
        render_page_heading(
            title="AI Workforce Assistant",
            description=(
                "Your intelligent assistant for workforce planning, consultant search "
                "and resource insights."
            ),
        )
    with heading_columns[1]:
        st.button(
            "New chat",
            icon=":material/add_comment:",
            use_container_width=True,
            on_click=_reset_chat,
        )

    st.caption("Suggested questions")
    suggestion_columns = st.columns(2)
    for index, question in enumerate(SUGGESTED_QUESTIONS):
        with suggestion_columns[index % 2]:
            if st.button(question, key=f"suggestion_{index}", use_container_width=True):
                st.session_state.workforce_pending_question = question
                st.rerun()

    st.divider()

    for message in st.session_state.workforce_messages:
        _render_message(message)

    pending_question = st.session_state.pop("workforce_pending_question", None)
    typed_question = st.chat_input("Ask a question...")
    question = typed_question or pending_question

    if question:
        _submit_question(question)
        st.rerun()
