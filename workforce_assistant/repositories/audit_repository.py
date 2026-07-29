from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from workforce_assistant.config.settings import settings


AUDIT_COLUMNS = [
    "timestamp",
    "event_type",
    "request_id",
    "user_id",
    "conversation_id",
    "question",
    "answer",
    "route",
    "report_name",
    "router_confidence",
    "response_time_ms",
    "table_row_count",
    "source_count",
    "table_count",
    "success",
    "exception",
]


def load_audit_events(
    *,
    limit: int = 500,
) -> pd.DataFrame:
    """
    Load the most recent chatbot audit events from the JSON log file.
    """

    log_file = (
        settings.log_dir
        / "workforce-assistant.log"
    )

    if not log_file.exists():
        return pd.DataFrame(
            columns=AUDIT_COLUMNS
        )

    events: list[dict[str, Any]] = []

    with log_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("event_type") not in {
                "chat_request_completed",
                "chat_request_failed",
            }:
                continue        

            events.append(event)

    if not events:
        return pd.DataFrame(
            columns=AUDIT_COLUMNS
        )

    recent_events = events[-limit:]

    dataframe = pd.DataFrame(
        recent_events
    )

    for column in AUDIT_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[
        AUDIT_COLUMNS
    ]

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        errors="coerce",
        utc=True,
    )

    dataframe = dataframe.sort_values(
        "timestamp",
        ascending=False,
        na_position="last",
    )

    return dataframe.reset_index(
        drop=True
    )