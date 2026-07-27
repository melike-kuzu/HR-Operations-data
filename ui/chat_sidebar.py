from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import streamlit as st

from workforce_assistant.domain.conversation_models import (
    Conversation,
)


def _conversation_group_label(
    updated_at: datetime,
) -> str:
    now = datetime.now(timezone.utc)

    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(
            tzinfo=timezone.utc
        )

    day_difference = (
        now.date() - updated_at.date()
    ).days

    if day_difference == 0:
        return "Today"

    if day_difference == 1:
        return "Yesterday"

    if day_difference <= 7:
        return "Previous 7 days"

    return "Older"


def render_chat_sidebar(
    *,
    conversations: list[Conversation],
    active_conversation_id: str | None,
    user_display_name: str,
    on_new_chat: Callable[[], None],
    on_select_chat: Callable[[str], None],
    on_archive_chat: Callable[[str], None],
) -> None:
    with st.sidebar:
        st.divider()

        st.caption(
            f"Signed in as {user_display_name}"
        )

        st.subheader("Chats")

        if st.button(
            "New chat",
            key="sidebar_new_chat",
            icon=":material/add_comment:",
            use_container_width=True,
        ):
            on_new_chat()

        if not conversations:
            st.caption("No saved conversations yet.")
            return

        grouped: dict[str, list[Conversation]] = {}

        for conversation in conversations:
            label = _conversation_group_label(
                conversation.updated_at
            )
            grouped.setdefault(label, []).append(
                conversation
            )

        for group_name in (
            "Today",
            "Yesterday",
            "Previous 7 days",
            "Older",
        ):
            group = grouped.get(group_name)

            if not group:
                continue

            st.caption(group_name)

            for conversation in group:
                columns = st.columns([6, 1])

                is_active = (
                    conversation.conversation_id
                    == active_conversation_id
                )

                button_label = conversation.title

                if is_active:
                    button_label = f"• {button_label}"

                with columns[0]:
                    if st.button(
                        button_label,
                        key=(
                            "conversation_"
                            f"{conversation.conversation_id}"
                        ),
                        use_container_width=True,
                    ):
                        on_select_chat(
                            conversation.conversation_id
                        )

                with columns[1]:
                    if st.button(
                        "×",
                        key=(
                            "archive_"
                            f"{conversation.conversation_id}"
                        ),
                        help="Archive conversation",
                        use_container_width=True,
                    ):
                        on_archive_chat(
                            conversation.conversation_id
                        )