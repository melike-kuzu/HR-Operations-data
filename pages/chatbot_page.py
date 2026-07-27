"""AI Workforce Assistant page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ui.chat_sidebar import render_chat_sidebar
from ui.layout import render_page_heading
from workforce_assistant.domain.conversation_models import (
    ConversationMessage,
)
from workforce_assistant.services.chatbot_service import (
    ask_data_question,
)
from workforce_assistant.services.service_factory import (
    get_conversation_service,
    get_user_service,
)


SUGGESTED_QUESTIONS = (
    "Who knows Azure?",
    "Who is on bench today?",
    "Who becomes available next month?",
    "Find an AWS consultant with banking experience.",
)

WELCOME_MESSAGE = (
    "Hi! I can help you find consultants, review availability, "
    "search skills and experience, and explore workforce and "
    "project information."
)

ACTIVE_CONVERSATION_KEY = (
    "workforce_active_conversation_id"
)

PENDING_QUESTION_KEY = (
    "workforce_pending_question"
)

RUNTIME_TABLES_KEY = (
    "workforce_runtime_tables"
)


def _get_services():
    conversation_service = (
        get_conversation_service()
    )
    current_user = (
        get_user_service().get_current_user()
    )

    return conversation_service, current_user


def _ensure_runtime_state() -> None:
    if RUNTIME_TABLES_KEY not in st.session_state:
        st.session_state[RUNTIME_TABLES_KEY] = {}


def _create_new_conversation() -> str:
    conversation_service, current_user = (
        _get_services()
    )

    conversation = (
        conversation_service.create_conversation(
            user_id=current_user.user_id
        )
    )

    st.session_state[
        ACTIVE_CONVERSATION_KEY
    ] = conversation.conversation_id

    st.session_state[
        RUNTIME_TABLES_KEY
    ] = {}

    return conversation.conversation_id


def _get_active_conversation_id() -> str:
    conversation_service, current_user = (
        _get_services()
    )

    active_id = st.session_state.get(
        ACTIVE_CONVERSATION_KEY
    )

    if active_id:
        conversation = (
            conversation_service.get_conversation(
                active_id,
                user_id=current_user.user_id,
            )
        )

        if (
            conversation is not None
            and not conversation.is_archived
        ):
            return active_id

    conversations = (
        conversation_service.list_conversations(
            user_id=current_user.user_id,
            limit=50,
        )
    )

    if conversations:
        active_id = conversations[
            0
        ].conversation_id

        st.session_state[
            ACTIVE_CONVERSATION_KEY
        ] = active_id

        return active_id

    return _create_new_conversation()


def _new_chat() -> None:
    _create_new_conversation()
    st.session_state.pop(
        PENDING_QUESTION_KEY,
        None,
    )
    st.rerun()


def _select_chat(
    conversation_id: str,
) -> None:
    st.session_state[
        ACTIVE_CONVERSATION_KEY
    ] = conversation_id

    st.session_state[
        RUNTIME_TABLES_KEY
    ] = {}

    st.rerun()


def _archive_chat(
    conversation_id: str,
) -> None:
    conversation_service, current_user = (
        _get_services()
    )

    conversation_service.archive_conversation(
        conversation_id,
        user_id=current_user.user_id,
    )

    if (
        st.session_state.get(
            ACTIVE_CONVERSATION_KEY
        )
        == conversation_id
    ):
        st.session_state.pop(
            ACTIVE_CONVERSATION_KEY,
            None,
        )

    st.session_state[
        RUNTIME_TABLES_KEY
    ] = {}

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


def _runtime_table_for_message(
    message_id: str,
) -> pd.DataFrame:
    runtime_tables = st.session_state.get(
        RUNTIME_TABLES_KEY,
        {},
    )

    table = runtime_tables.get(message_id)

    if isinstance(table, pd.DataFrame):
        return table

    return pd.DataFrame()


def _render_message(
    message: ConversationMessage,
) -> None:
    with st.chat_message(message.role):
        st.markdown(message.content)

        if message.sources:
            chips = "".join(
                (
                    '<span class="source-chip">'
                    f"{source}"
                    "</span>"
                )
                for source in message.sources
            )

            st.markdown(
                chips,
                unsafe_allow_html=True,
            )

        table = _runtime_table_for_message(
            message.message_id
        )

        if not table.empty:
            with st.expander(
                (
                    "View supporting data "
                    f"({len(table)} records)"
                ),
                expanded=True,
            ):
                st.dataframe(
                    table,
                    use_container_width=True,
                    hide_index=True,
                    height=min(
                        420,
                        42 + len(table) * 35,
                    ),
                )

        elif message.metadata.get(
            "table_row_count"
        ):
            st.caption(
                "Supporting table metadata was saved, "
                "but the live DataFrame is no longer "
                "available after the application rerun."
            )


def _extract_first_table(
    result: dict[str, Any],
) -> pd.DataFrame:
    table = result.get("table")

    if isinstance(table, pd.DataFrame):
        return table

    tables = result.get("tables", {})

    if isinstance(tables, dict):
        for value in tables.values():
            if isinstance(value, pd.DataFrame):
                return value

    return pd.DataFrame()


def _table_metadata(
    table: pd.DataFrame,
) -> dict[str, Any]:
    if table.empty:
        return {
            "table_row_count": 0,
            "table_columns": [],
        }

    return {
        "table_row_count": len(table),
        "table_columns": [
            str(column)
            for column in table.columns
        ],
    }


def _submit_question(
    question: str,
    *,
    conversation_id: str,
) -> None:
    clean_question = question.strip()

    if not clean_question:
        return

    conversation_service, current_user = (
        _get_services()
    )

    conversation_service.add_message(
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        role="user",
        content=clean_question,
    )

    try:
        with st.spinner(
            "Analysing workforce data..."
        ):
            result = ask_data_question(
                clean_question,
                user_id=current_user.user_id,
                conversation_id=conversation_id,
            )

        answer = str(
            result.get(
                "answer",
                (
                    "The request was processed, but "
                    "no written answer was returned."
                ),
            )
        )

        sources = [
            str(source)
            for source in result.get(
                "sources",
                [],
            )
        ]

        route = result.get("route")
        metadata = dict(
            result.get("metadata", {})
        )

        table = _extract_first_table(result)

        metadata.update(
            _table_metadata(table)
        )

    except Exception as error:
        answer = (
            "I could not complete that request. "
            f"Error: {error}"
        )
        sources = []
        route = "error"
        metadata = {
            "success": False,
            "error_type": type(error).__name__,
        }
        table = pd.DataFrame()

    assistant_message = (
        conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=current_user.user_id,
            role="assistant",
            content=answer,
            route=(
                str(route)
                if route is not None
                else None
            ),
            sources=sources,
            metadata=metadata,
        )
    )

    if not table.empty:
        st.session_state[
            RUNTIME_TABLES_KEY
        ][assistant_message.message_id] = table


def _render_sidebar(
    *,
    conversation_id: str,
) -> None:
    conversation_service, current_user = (
        _get_services()
    )

    conversations = (
        conversation_service.list_conversations(
            user_id=current_user.user_id,
            limit=50,
        )
    )

    render_chat_sidebar(
        conversations=conversations,
        active_conversation_id=conversation_id,
        user_display_name=(
            current_user.display_name
        ),
        on_new_chat=_new_chat,
        on_select_chat=_select_chat,
        on_archive_chat=_archive_chat,
    )


def render() -> None:
    _ensure_runtime_state()
    _render_styles()

    conversation_service, current_user = (
        _get_services()
    )

    conversation_id = (
        _get_active_conversation_id()
    )

    _render_sidebar(
        conversation_id=conversation_id
    )

    heading_columns = st.columns([5, 1])

    with heading_columns[0]:
        render_page_heading(
            title="AI Workforce Assistant",
            description=(
                "Your intelligent assistant for workforce "
                "planning, consultant search and resource "
                "insights."
            ),
        )

    with heading_columns[1]:
        if st.button(
            "New chat",
            icon=":material/add_comment:",
            use_container_width=True,
        ):
            _new_chat()

    st.caption("Suggested questions")

    suggestion_columns = st.columns(2)

    for index, question in enumerate(
        SUGGESTED_QUESTIONS
    ):
        with suggestion_columns[index % 2]:
            if st.button(
                question,
                key=f"suggestion_{index}",
                use_container_width=True,
            ):
                st.session_state[
                    PENDING_QUESTION_KEY
                ] = question
                st.rerun()

    st.divider()

    messages = conversation_service.get_messages(
        conversation_id,
        user_id=current_user.user_id,
    )

    if not messages:
        with st.chat_message("assistant"):
            st.markdown(WELCOME_MESSAGE)

    for message in messages:
        _render_message(message)

    pending_question = (
        st.session_state.pop(
            PENDING_QUESTION_KEY,
            None,
        )
    )

    typed_question = st.chat_input(
        "Ask a question..."
    )

    question = (
        typed_question
        or pending_question
    )

    if question:
        _submit_question(
            question,
            conversation_id=conversation_id,
        )
        st.rerun()