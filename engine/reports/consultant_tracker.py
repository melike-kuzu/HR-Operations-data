from __future__ import annotations

import pandas as pd

from engine.master_dataset import MasterData
from engine.business_logic import build_consultant_calendar_base


def build_consultant_calendar(
    data: MasterData,
) -> pd.DataFrame:
    """
    Consultant Tracker için uzun format calendar üretir.
    """

    calendar = build_consultant_calendar_base(data)

    calendar = calendar.sort_values(
        [
            "Group",
            "Consultant_Name",
            "WeekStart",
        ]
    ).reset_index(drop=True)

    return calendar


def calendar_to_tracker(
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    """
    Uzun formattaki consultant calendar verisini,
    haftaların kolon olduğu geniş Consultant Tracker tablosuna çevirir.
    """

    required_columns = {
        "Group",
        "Consultant_Name",
        "Expected_Availability_Date",
        "Active_Projects",
        "WeekStart",
        "CalendarValue",
    }

    missing_columns = required_columns.difference(calendar.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(
            "Consultant calendar is missing columns: "
            f"{missing_text}"
        )

    tracker = calendar.pivot_table(
        index=[
            "Group",
            "Consultant_Name",
            "Expected_Availability_Date",
            "Active_Projects",
        ],
        columns="WeekStart",
        values="CalendarValue",
        aggfunc="first",
        dropna=False,
    )

    tracker = tracker.reset_index()
    tracker.columns.name = None

    date_columns = [
        column
        for column in tracker.columns
        if isinstance(column, pd.Timestamp)
    ]

    tracker = tracker.rename(
        columns={
            column: column.strftime("%Y-%m-%d")
            for column in date_columns
        }
    )

    fixed_columns = [
        "Group",
        "Consultant_Name",
        "Expected_Availability_Date",
        "Active_Projects",
    ]

    weekly_columns = sorted(
        [
            column
            for column in tracker.columns
            if column not in fixed_columns
        ]
    )

    tracker = tracker[
        fixed_columns + weekly_columns
    ]

    tracker = tracker.sort_values(
        [
            "Group",
            "Consultant_Name",
        ],
        na_position="last",
    ).reset_index(drop=True)

    return tracker


def build_consultant_tracker(
    data: MasterData,
) -> pd.DataFrame:
    """
    Dashboard'da gösterilecek Consultant Tracker tablosunu üretir.
    """

    calendar = build_consultant_calendar(data)

    tracker = calendar_to_tracker(calendar)

    return tracker