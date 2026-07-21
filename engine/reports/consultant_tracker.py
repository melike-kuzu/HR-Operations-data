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
    danışman başına tek satır ve haftalar kolon olacak
    şekilde Consultant Tracker tablosuna çevirir.

    Her haftanın görünen CalendarValue kolonuna ek olarak,
    arayüzde doğru hücre renginin belirlenebilmesi için
    YYYY-MM-DD__STATUS kolonları da oluşturulur.
    """

    required_columns = {
        "Group",
        "Consultant_Name",
        "Expected_Availability_Date",
        "Active_Projects",
        "WeekStart",
        "CalendarValue",
        "CalendarStatus",
    }

    missing_columns = required_columns.difference(
        calendar.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Consultant calendar is missing columns: "
            f"{missing_text}"
        )

    working = calendar.copy()

    working["WeekStart"] = pd.to_datetime(
        working["WeekStart"],
        errors="coerce",
    ).dt.normalize()

    working["Expected_Availability_Date"] = (
        pd.to_datetime(
            working["Expected_Availability_Date"],
            errors="coerce",
        )
        .dt.normalize()
    )

    working = working.dropna(
        subset=[
            "Consultant_Name",
            "WeekStart",
        ]
    )

    consultant_key_columns = [
        "Group",
        "Consultant_Name",
    ]

    consultant_week_columns = [
        "Group",
        "Consultant_Name",
        "WeekStart",
    ]

    # Her consultant ve hafta için yalnızca tek CalendarValue bırak.
    weekly_values = (
        working[
            consultant_week_columns
            + [
                "CalendarValue",
            ]
        ]
        .drop_duplicates(
            subset=consultant_week_columns,
            keep="first",
        )
    )

    value_tracker = weekly_values.pivot(
        index=consultant_key_columns,
        columns="WeekStart",
        values="CalendarValue",
    ).reset_index()

    value_tracker.columns.name = None

    value_date_columns = [
        column
        for column in value_tracker.columns
        if isinstance(column, pd.Timestamp)
    ]

    value_tracker = value_tracker.rename(
        columns={
            column: column.strftime("%Y-%m-%d")
            for column in value_date_columns
        }
    )

    # Her consultant ve hafta için CalendarStatus değerini üret.
    # Bu kolonlar daha sonra report grid içerisinde gizlenecek
    # ve yalnızca hücre renklendirmesinde kullanılacak.
    weekly_statuses = (
        working[
            consultant_week_columns
            + [
                "CalendarStatus",
            ]
        ]
        .drop_duplicates(
            subset=consultant_week_columns,
            keep="first",
        )
    )

    status_tracker = weekly_statuses.pivot(
        index=consultant_key_columns,
        columns="WeekStart",
        values="CalendarStatus",
    ).reset_index()

    status_tracker.columns.name = None

    status_date_columns = [
        column
        for column in status_tracker.columns
        if isinstance(column, pd.Timestamp)
    ]

    status_tracker = status_tracker.rename(
        columns={
            column: (
                f"{column.strftime('%Y-%m-%d')}__STATUS"
            )
            for column in status_date_columns
        }
    )

    tracker = value_tracker.merge(
        status_tracker,
        on=consultant_key_columns,
        how="left",
        validate="one_to_one",
    )

    # Consultant seviyesindeki metadata ayrı hesaplanır.
    consultant_metadata = (
        working[
            consultant_key_columns
            + [
                "Expected_Availability_Date",
                "Active_Projects",
            ]
        ]
        .sort_values(
            consultant_key_columns
            + [
                "Expected_Availability_Date",
            ],
            na_position="last",
        )
        .groupby(
            consultant_key_columns,
            as_index=False,
            dropna=False,
        )
        .agg(
            Expected_Availability_Date=(
                "Expected_Availability_Date",
                "first",
            ),
            Active_Projects=(
                "Active_Projects",
                "max",
            ),
        )
    )

    tracker = consultant_metadata.merge(
        tracker,
        on=consultant_key_columns,
        how="left",
        validate="one_to_one",
    )

    # Saat bilgisini kaldır ve yalnızca YYYY-MM-DD göster.
    expected_availability = pd.to_datetime(
        tracker["Expected_Availability_Date"],
        errors="coerce",
    )

    tracker["Expected_Availability_Date"] = (
        expected_availability.dt.strftime(
            "%Y-%m-%d"
        )
    )

    tracker.loc[
        expected_availability.isna(),
        "Expected_Availability_Date",
    ] = None

    tracker["Active_Projects"] = (
        pd.to_numeric(
            tracker["Active_Projects"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    fixed_columns = [
        "Group",
        "Consultant_Name",
        "Expected_Availability_Date",
        "Active_Projects",
    ]

    weekly_value_columns = sorted(
        [
            column
            for column in tracker.columns
            if (
                column not in fixed_columns
                and not str(column).endswith(
                    "__STATUS"
                )
            )
        ]
    )

    weekly_status_columns = [
        f"{column}__STATUS"
        for column in weekly_value_columns
        if f"{column}__STATUS" in tracker.columns
    ]

    tracker = tracker[
        fixed_columns
        + weekly_value_columns
        + weekly_status_columns
    ]

    tracker = tracker.sort_values(
        consultant_key_columns,
        na_position="last",
    ).reset_index(drop=True)

    return tracker


def build_consultant_tracker(
    data: MasterData,
) -> pd.DataFrame:
    """
    Dashboard'da gösterilecek Consultant Tracker
    tablosunu üretir.
    """

    calendar = build_consultant_calendar(
        data
    )

    tracker = calendar_to_tracker(
        calendar
    )

    return tracker