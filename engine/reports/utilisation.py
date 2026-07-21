from __future__ import annotations

from datetime import date

import pandas as pd

from engine.master_dataset import MasterData
from engine.business_logic import build_consultant_calendar_base


UTILISATION_METRICS = [
    "Booked",
    "Unconfirmed",
    "Partly Booked",
    "On Leave",
    "Bench",
    "Booked Capacity",
    "Maximum Capacity",
    "Forecasted Allocation",
]


def _validate_calendar(calendar: pd.DataFrame) -> None:
    """
    Utilisation raporu için gerekli calendar kolonlarını kontrol eder.
    """

    required_columns = {
        "WeekStart",
        "CalendarStatus",
        "CalendarCapacity",
    }

    missing_columns = required_columns.difference(calendar.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(
            "Consultant calendar is missing columns: "
            f"{missing_text}"
        )


def _format_count(value: int | float) -> str:
    """
    SQL çıktısındaki count değerleri gibi tam sayı string üretir.
    """

    return str(int(value))


def _format_decimal_2(value: int | float) -> str:
    """
    SQL decimal(10,2) formatını üretir.
    """

    return f"{float(value):.2f}"


def _format_decimal_6(
    value: float | None,
) -> str | None:
    """
    SQL decimal(10,6) formatını üretir.

    SQL'deki NULLIF davranışına uygun olarak, Maximum Capacity
    sıfırsa None döndürülür.
    """

    if value is None or pd.isna(value):
        return None

    return f"{float(value):.6f}"


def calendar_to_utilisation(
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    """
    Uzun formattaki consultant calendar verisini,
    legacy SQL utilisation tablosuyla aynı yapıya çevirir.

    Satırlar:
        Booked
        Unconfirmed
        Partly Booked
        On Leave
        Bench
        Booked Capacity
        Maximum Capacity
        Forecasted Allocation

    Kolonlar:
        Utilisation
        YYYY-MM-DD formatındaki haftalar
    """

    _validate_calendar(calendar)

    if calendar.empty:
        return pd.DataFrame(
            columns=["Utilisation"]
        )

    working = calendar.copy()

    working["WeekStart"] = pd.to_datetime(
        working["WeekStart"],
        errors="raise",
    ).dt.normalize()

    working["CalendarStatus"] = (
        working["CalendarStatus"]
        .fillna("")
        .astype(str)
    )

    working["CalendarCapacity"] = pd.to_numeric(
        working["CalendarCapacity"],
        errors="coerce",
    ).fillna(0.0)

    weekly_rows: list[dict[str, object]] = []

    for week_start, week_data in working.groupby(
        "WeekStart",
        sort=True,
    ):
        statuses = week_data["CalendarStatus"]

        booked = statuses.eq("BOOKED").sum()

        unconfirmed = statuses.eq(
            "UNCONFIRMED"
        ).sum()

        partly_booked = statuses.eq(
            "PARTLY_BOOKED"
        ).sum()

        on_leave = statuses.eq(
            "ON_LEAVE"
        ).sum()

        bench = statuses.eq("BENCH").sum()

        booked_capacity_mask = statuses.isin(
            [
                "BOOKED",
                "PARTLY_BOOKED",
            ]
        )

        booked_capacity = (
            week_data.loc[
                booked_capacity_mask,
                "CalendarCapacity",
            ]
            .sum()
        )

        maximum_capacity = statuses.ne(
            "ON_LEAVE"
        ).sum()

        if maximum_capacity == 0:
            forecasted_allocation = None
        else:
            forecasted_allocation = (
                booked_capacity
                / float(maximum_capacity)
            )

        weekly_rows.extend(
            [
                {
                    "MetricOrder": 1,
                    "Utilisation": "Booked",
                    "WeekStart": week_start,
                    "MetricValue": _format_count(
                        booked
                    ),
                },
                {
                    "MetricOrder": 2,
                    "Utilisation": "Unconfirmed",
                    "WeekStart": week_start,
                    "MetricValue": _format_count(
                        unconfirmed
                    ),
                },
                {
                    "MetricOrder": 3,
                    "Utilisation": "Partly Booked",
                    "WeekStart": week_start,
                    "MetricValue": _format_count(
                        partly_booked
                    ),
                },
                {
                    "MetricOrder": 4,
                    "Utilisation": "On Leave",
                    "WeekStart": week_start,
                    "MetricValue": _format_count(
                        on_leave
                    ),
                },
                {
                    "MetricOrder": 5,
                    "Utilisation": "Bench",
                    "WeekStart": week_start,
                    "MetricValue": _format_count(
                        bench
                    ),
                },
                {
                    "MetricOrder": 6,
                    "Utilisation": "Booked Capacity",
                    "WeekStart": week_start,
                    "MetricValue": _format_decimal_2(
                        booked_capacity
                    ),
                },
                {
                    "MetricOrder": 7,
                    "Utilisation": "Maximum Capacity",
                    "WeekStart": week_start,
                    "MetricValue": _format_decimal_2(
                        maximum_capacity
                    ),
                },
                {
                    "MetricOrder": 8,
                    "Utilisation": "Forecasted Allocation",
                    "WeekStart": week_start,
                    "MetricValue": _format_decimal_6(
                        forecasted_allocation
                    ),
                },
            ]
        )

    utilisation_long = pd.DataFrame(
        weekly_rows
    )

    utilisation = utilisation_long.pivot(
    index=[
        "MetricOrder",
        "Utilisation",
    ],
    columns="WeekStart",
    values="MetricValue",
)

    utilisation = (
    utilisation
    .reset_index()
    .sort_values("MetricOrder")
    .drop(columns="MetricOrder")
    .reset_index(drop=True)
)

    utilisation.columns.name = None

    date_columns = [
        column
        for column in utilisation.columns
        if isinstance(column, pd.Timestamp)
    ]

    utilisation = utilisation.rename(
        columns={
            column: column.strftime("%Y-%m-%d")
            for column in date_columns
        }
    )

    weekly_columns = sorted(
        [
            column
            for column in utilisation.columns
            if column != "Utilisation"
        ]
    )

    utilisation = utilisation[
        ["Utilisation"] + weekly_columns
    ]

    return utilisation


def build_utilisation(
    data: MasterData,
    run_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Dashboard'da gösterilecek haftalık utilisation
    özet tablosunu üretir.

    run_date:
        None olduğunda bugünün tarihini kullanır.

        Testlerde veya geçmiş tarihli raporlarda sabit bir tarih
        verilebilir:

        build_utilisation(
            data,
            run_date="2026-07-20",
        )
    """

    calendar = build_consultant_calendar_base(
        data=data,
        as_of_date=run_date,
    )

    utilisation = calendar_to_utilisation(
        calendar
    )

    return utilisation


def build_utilisation_detailed(
    data: MasterData,
    run_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Consultant bazında haftalık utilisation detay tablosunu üretir.

    Her satır bir consultant'ı temsil eder.
    Haftalık kolonlarda CalendarValue bulunur:

        B    = Bench
        L    = On Leave
        1.00 = Fully booked / unconfirmed
        0.50 = Partly booked
    """

    calendar = build_consultant_calendar_base(
        data=data,
        as_of_date=run_date,
    ).copy()

    required_columns = {
        "Consultant_Name",
        "Level",
        "Group",
        "Location",
        "WeekStart",
        "CalendarValue",
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

    if calendar.empty:
        return pd.DataFrame(
            columns=[
                "Consultant_Name",
                "Level",
                "Group",
                "Location",
            ]
        )

    calendar["WeekStart"] = pd.to_datetime(
        calendar["WeekStart"],
        errors="raise",
    ).dt.normalize()

    row_columns = [
        "Consultant_Name",
        "Level",
        "Group",
        "Location",
    ]

    detailed = calendar.pivot(
        index=row_columns,
        columns="WeekStart",
        values="CalendarValue",
    )

    detailed = detailed.reset_index()

    detailed.columns.name = None

    date_columns = [
        column
        for column in detailed.columns
        if isinstance(column, pd.Timestamp)
    ]

    detailed = detailed.rename(
        columns={
            column: column.strftime("%Y-%m-%d")
            for column in date_columns
        }
    )

    weekly_columns = sorted(
        [
            column
            for column in detailed.columns
            if column not in row_columns
        ]
    )

    detailed = detailed[
        row_columns + weekly_columns
    ]

    detailed = detailed.sort_values(
        [
            "Consultant_Name",
            "Level",
            "Group",
            "Location",
        ],
        na_position="last",
    ).reset_index(drop=True)

    return detailed