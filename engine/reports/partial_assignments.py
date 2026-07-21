from __future__ import annotations

from datetime import date

import pandas as pd

from engine.master_dataset import MasterData


OUTPUT_COLUMNS = [
    "Resource ID",
    "Resource name",
    "Level",
    "Group",
    "Client",
    "Weeks assigned to project (<100% billable)",
    "Time (%)",
]


def _require_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    missing_columns = required_columns.difference(
        dataframe.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"{dataset_name} is missing columns: "
            f"{missing_text}"
        )


def _get_current_week_start(
    run_date: str | date | pd.Timestamp | None,
) -> pd.Timestamp:
    selected_date = (
        pd.Timestamp.today().normalize()
        if run_date is None
        else pd.Timestamp(run_date).normalize()
    )

    return (
        selected_date
        - pd.Timedelta(
            days=selected_date.weekday()
        )
    )


def build_partial_assignments(
    data: MasterData,
    run_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Builds the Partial Assignments report.

    Business rules:
    - Only assignments active on run_date are included.
    - The current incomplete week is excluded.
    - The previous 52 completed weeks are included.
    - Hours are aggregated by consultant, project and week.
    - A week is partial when 0 < Logged_Hours < 40.
    - Time (%) is the average partial capacity.
    """

    selected_date = (
        pd.Timestamp.today().normalize()
        if run_date is None
        else pd.Timestamp(run_date).normalize()
    )

    current_week_start = _get_current_week_start(
        run_date
    )

    window_start = (
        current_week_start
        - pd.Timedelta(weeks=52)
    )

    #assignments = data.assignments.copy()

    from engine.business_logic import get_eligible_assignments

    assignments = get_eligible_assignments(
        data.assignments,
        as_of_date=selected_date,
    ).copy()
    time_entries = data.time_entries.copy()

    assignment_required_columns = {
        "Resource_Id",
        "ActivityAssignment_Id",
        "Consultant_Name",
        "Level",
        "Group",
        "Project_Name",
        "PROJECT_ID",
        "Assignment_Start",
        "Assignment_End",
    }

    time_entry_required_columns = {
        "ActivityAssignment_Id",
        "WeekStart",
        "Logged_Hours",
    }

    _require_columns(
        assignments,
        assignment_required_columns,
        "Assignments data",
    )

    _require_columns(
        time_entries,
        time_entry_required_columns,
        "Time entries data",
    )

    assignments["Assignment_Start"] = pd.to_datetime(
        assignments["Assignment_Start"],
        errors="coerce",
    ).dt.normalize()

    assignments["Assignment_End"] = pd.to_datetime(
        assignments["Assignment_End"],
        errors="coerce",
    ).dt.normalize()

    time_entries["WeekStart"] = pd.to_datetime(
        time_entries["WeekStart"],
        errors="coerce",
    ).dt.normalize()

    time_entries["Logged_Hours"] = pd.to_numeric(
        time_entries["Logged_Hours"],
        errors="coerce",
    ).fillna(0.0)

    active_assignment_mask = (
        assignments[
            "ActivityAssignment_Id"
        ].notna()
        & assignments["PROJECT_ID"].notna()
        & assignments["Project_Name"].notna()
        & assignments[
            "Assignment_Start"
        ].notna()
        & assignments[
            "Assignment_Start"
        ].le(selected_date)
        & (
            assignments[
                "Assignment_End"
            ].isna()
            | assignments[
                "Assignment_End"
            ].ge(selected_date)
        )
    )

    active_assignments = assignments.loc[
        active_assignment_mask,
        [
            "Resource_Id",
            "ActivityAssignment_Id",
            "Consultant_Name",
            "Level",
            "Group",
            "Project_Name",
            "PROJECT_ID",
        ],
    ].copy()

    if active_assignments.empty:
        return pd.DataFrame(
            columns=OUTPUT_COLUMNS
        )

    historical_time_entries = time_entries.loc[
        time_entries["WeekStart"].notna()
        & time_entries["WeekStart"].ge(
            window_start
        )
        & time_entries["WeekStart"].lt(
            current_week_start
        ),
        [
            "ActivityAssignment_Id",
            "WeekStart",
            "Logged_Hours",
        ],
    ].copy()

    if historical_time_entries.empty:
        return pd.DataFrame(
            columns=OUTPUT_COLUMNS
        )

    assignment_entries = active_assignments.merge(
        historical_time_entries,
        on="ActivityAssignment_Id",
        how="inner",
        validate="one_to_many",
    )

    if assignment_entries.empty:
        return pd.DataFrame(
            columns=OUTPUT_COLUMNS
        )

    weekly_grouping_columns = [
        "Resource_Id",
        "Consultant_Name",
        "Level",
        "Group",
        "Project_Name",
        "PROJECT_ID",
        "WeekStart",
    ]

    weekly_project_hours = (
        assignment_entries
        .groupby(
            weekly_grouping_columns,
            as_index=False,
            dropna=False,
        )["Logged_Hours"]
        .sum()
    )

    partial_weeks = weekly_project_hours.loc[
        weekly_project_hours[
            "Logged_Hours"
        ].gt(0)
        & weekly_project_hours[
            "Logged_Hours"
        ].lt(40)
    ].copy()

    if partial_weeks.empty:
        return pd.DataFrame(
            columns=OUTPUT_COLUMNS
        )

    partial_weeks["Partial_Capacity"] = (
        partial_weeks["Logged_Hours"]
        / 40.0
    )

    summary_grouping_columns = [
        "Resource_Id",
        "Consultant_Name",
        "Level",
        "Group",
        "Project_Name",
        "PROJECT_ID",
    ]

    partial_summary = (
        partial_weeks
        .groupby(
            summary_grouping_columns,
            as_index=False,
            dropna=False,
        )
        .agg(
            Partial_Weeks=(
                "WeekStart",
                "size",
            ),
            Average_Partial_Capacity=(
                "Partial_Capacity",
                "mean",
            ),
        )
    )

    partial_summary[
        "Weeks assigned to project (<100% billable)"
    ] = (
        partial_summary["Partial_Weeks"]
        .astype("Int64")
    )

    partial_summary["Time (%)"] = (
        partial_summary[
            "Average_Partial_Capacity"
        ]
        .mul(100)
        .round(2)
    )

    report = partial_summary.rename(
        columns={
            "Resource_Id": "Resource ID",
            "Consultant_Name": "Resource name",
            "Project_Name": "Client",
        }
    )

    report = report.loc[
        report[
            "Weeks assigned to project (<100% billable)"
        ].gt(0),
        OUTPUT_COLUMNS,
    ]

    report = (
        report
        .sort_values(
            [
                "Weeks assigned to project (<100% billable)",
                "Resource name",
                "Client",
            ],
            ascending=[
                False,
                True,
                True,
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    return report