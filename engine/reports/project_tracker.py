from __future__ import annotations

from datetime import date, datetime

import pandas as pd


DateInput = str | date | datetime | pd.Timestamp | None


def _normalise_run_date(run_date: DateInput = None) -> pd.Timestamp:
    """
    SQL'deki GETDATE() karşılığıdır.
    Sabit yıl veya sabit tarih kullanılmaz.
    """
    if run_date is None:
        return pd.Timestamp.today().normalize()

    return pd.Timestamp(
        pd.to_datetime(run_date, errors="raise")
    ).normalize()


def _get_this_week_start(run_date: DateInput = None) -> pd.Timestamp:
    """
    SQL:
        DATEADD(WEEK, DATEDIFF(WEEK, 0, GETDATE()), 0)

    İçinde bulunulan haftanın pazartesi gününü döndürür.
    """
    current_date = _normalise_run_date(run_date)

    return (
        current_date
        - pd.Timedelta(days=current_date.weekday())
    ).normalize()


def _combine_leave_info(values: pd.Series) -> str:
    """
    Aynı resource ve hafta için birden fazla leave açıklaması varsa
    SQL STRING_AGG davranışına benzer şekilde birleştirir.
    """
    result: list[str] = []

    for value in values:
        if pd.isna(value):
            continue

        text = str(value).strip()

        if not text:
            continue

        if text.lower() in {"nan", "none"}:
            continue

        if text not in result:
            result.append(text)

    if not result:
        return "0 hours"

    return ", ".join(result)


def _prepare_assignments(assignments: pd.DataFrame) -> pd.DataFrame:
    """
    SQL'deki Base CTE karşılığıdır.

    SQL Base filtresi:
        Consultant_Name IS NOT NULL
        Project_Name IS NOT NULL

    Assignment tarihine göre ek filtre uygulanmaz.
    """
    required_columns = [
        "ActivityAssignment_Id",
        "Resource_Id",
        "Consultant_Name",
        "Level",
        "Job_Title",
        "Location",
        "Project_Name",
        "Project_Type",
        "Project_Status",
        "Assignment_Start",
        "Assignment_End",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in assignments.columns
    ]

    if missing_columns:
        raise ValueError(
            "assignments verisinde eksik kolonlar var: "
            + ", ".join(missing_columns)
        )

    base = assignments[required_columns].copy()

    base["Consultant_Name"] = (
        base["Consultant_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    base["Project_Name"] = (
        base["Project_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    base = base.loc[
        base["Consultant_Name"].ne("")
        & base["Project_Name"].ne("")
    ].copy()

    base["Assignment_Start"] = pd.to_datetime(
        base["Assignment_Start"],
        errors="coerce",
    )

    base["Assignment_End"] = pd.to_datetime(
        base["Assignment_End"],
        errors="coerce",
    )

    return base.reset_index(drop=True)


def _prepare_time_entries(
    time_entries: pd.DataFrame,
    this_week_start: pd.Timestamp,
) -> pd.DataFrame:
    """
    SQL'deki TimeEntryAgg CTE karşılığıdır.

    Zaman aralığı:
        this_week_start - 1 yıl
        this_week_start'tan küçük
    """
    required_columns = [
        "ActivityAssignment_Id",
        "WeekStart",
        "Logged_Hours",
        "Consumed_Days",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in time_entries.columns
    ]

    if missing_columns:
        raise ValueError(
            "time_entries verisinde eksik kolonlar var: "
            + ", ".join(missing_columns)
        )

    window_start = this_week_start - pd.DateOffset(years=1)

    time_entry_agg = time_entries[required_columns].copy()

    time_entry_agg["WeekStart"] = pd.to_datetime(
        time_entry_agg["WeekStart"],
        errors="coerce",
    ).dt.normalize()

    time_entry_agg["Logged_Hours"] = (
        pd.to_numeric(
            time_entry_agg["Logged_Hours"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    time_entry_agg["Consumed_Days"] = (
        pd.to_numeric(
            time_entry_agg["Consumed_Days"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    time_entry_agg = time_entry_agg.loc[
        time_entry_agg["ActivityAssignment_Id"].notna()
        & time_entry_agg["WeekStart"].ge(window_start)
        & time_entry_agg["WeekStart"].lt(this_week_start)
    ].copy()

    time_entry_agg = (
        time_entry_agg
        .groupby(
            [
                "ActivityAssignment_Id",
                "WeekStart",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            Logged_Hours=(
                "Logged_Hours",
                "sum",
            ),
            Consumed_Days=(
                "Consumed_Days",
                "sum",
            ),
        )
    )

    return time_entry_agg


def _build_submission_status(
    time_entries: pd.DataFrame,
    this_week_start: pd.Timestamp,
) -> pd.DataFrame:
    """
    SQL'deki SubmissionStatus CTE karşılığıdır.

    Bir assignment son 3 haftanın üçünde de pozitif saat içeriyorsa:
        Active

    Aksi durumda:
        Inactive
    """
    submission_window_start = (
        this_week_start
        - pd.Timedelta(weeks=3)
    )

    submission_source = time_entries.copy()

    submission_source["WeekStart"] = pd.to_datetime(
        submission_source["WeekStart"],
        errors="coerce",
    ).dt.normalize()

    submission_source["Logged_Hours"] = (
        pd.to_numeric(
            submission_source["Logged_Hours"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    submission_source = submission_source.loc[
        submission_source["ActivityAssignment_Id"].notna()
        & submission_source["WeekStart"].ge(
            submission_window_start
        )
        & submission_source["WeekStart"].lt(
            this_week_start
        )
        & submission_source["Logged_Hours"].gt(0)
    ].copy()

    if submission_source.empty:
        return pd.DataFrame(
            columns=[
                "ActivityAssignment_Id",
                "Submission",
            ]
        )

    submission_status = (
        submission_source
        .groupby(
            "ActivityAssignment_Id",
            as_index=False,
            dropna=False,
        )
        .agg(
            Submitted_Week_Count=(
                "WeekStart",
                "nunique",
            )
        )
    )

    submission_status["Submission"] = (
        submission_status["Submitted_Week_Count"]
        .eq(3)
        .map(
            {
                True: "Active",
                False: "Inactive",
            }
        )
    )

    return submission_status[
        [
            "ActivityAssignment_Id",
            "Submission",
        ]
    ]


def _prepare_leave(
    leave: pd.DataFrame,
    this_week_start: pd.Timestamp,
) -> pd.DataFrame:
    """
    SQL'deki LeaveWeekAgg karşılığıdır.

    weekly_leave.sql tarafından Leave_Info hazırlanmışsa doğrudan kullanılır.

    Örnek:
        32.00 hours (CPES Vacations 2026)

    Leave olmayan haftalarda final tabloda:
        0 hours
    """
    required_columns = [
        "Resource_Id",
        "WeekStart",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in leave.columns
    ]

    if missing_columns:
        raise ValueError(
            "leave verisinde eksik kolonlar var: "
            + ", ".join(missing_columns)
        )

    window_start = this_week_start - pd.DateOffset(years=1)

    leave_weekly = leave.copy()

    leave_weekly["WeekStart"] = pd.to_datetime(
        leave_weekly["WeekStart"],
        errors="coerce",
    ).dt.normalize()

    leave_weekly = leave_weekly.loc[
        leave_weekly["Resource_Id"].notna()
        & leave_weekly["WeekStart"].ge(window_start)
        & leave_weekly["WeekStart"].lt(this_week_start)
    ].copy()

    if "Leave_Info" not in leave_weekly.columns:
        if {
            "Leave_Hours",
            "Leave_Type",
        }.issubset(leave_weekly.columns):

            leave_weekly["Leave_Hours"] = pd.to_numeric(
                leave_weekly["Leave_Hours"],
                errors="coerce",
            ).fillna(0.0)

            leave_weekly["Leave_Info"] = (
                leave_weekly["Leave_Hours"]
                .map(lambda value: f"{value:.2f}")
                + " hours ("
                + leave_weekly["Leave_Type"]
                .fillna("Leave")
                .astype(str)
                + ")"
            )

        elif "Leave_Hours" in leave_weekly.columns:
            leave_weekly["Leave_Hours"] = pd.to_numeric(
                leave_weekly["Leave_Hours"],
                errors="coerce",
            ).fillna(0.0)

            leave_weekly["Leave_Info"] = (
                leave_weekly["Leave_Hours"]
                .map(lambda value: f"{value:.2f}")
                + " hours (Leave)"
            )

        else:
            leave_weekly["Leave_Info"] = ""

    leave_weekly["Leave_Info"] = (
        leave_weekly["Leave_Info"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    leave_weekly = (
        leave_weekly
        .groupby(
            [
                "Resource_Id",
                "WeekStart",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            Leave_Info=(
                "Leave_Info",
                _combine_leave_info,
            )
        )
    )

    return leave_weekly


def build_project_tracker(
    data,
    run_date: DateInput = None,
) -> pd.DataFrame:
    """
    Orijinal Project Tracker SQL'ini Python ile üretir.

    Final kolonlar:

        Consultant_Name
        Level
        Job_Title
        Location
        Project_Name
        Project_Type
        Submission
        Project_Status
        Assignment_Start
        Assignment_End

    Ardından her hafta için sırasıyla:

        Logged_Hours_YYYY-MM-DD
        Leave_YYYY-MM-DD
        Consumed_Days_YYYY-MM-DD

    Toplam 52 hafta gösterilir.
    En yeni tamamlanmış hafta önce gelir.
    """
    this_week_start = _get_this_week_start(run_date)

    base = _prepare_assignments(
        data.assignments
    )

    time_entry_agg = _prepare_time_entries(
        data.time_entries,
        this_week_start=this_week_start,
    )

    submission_status = _build_submission_status(
        data.time_entries,
        this_week_start=this_week_start,
    )

    leave_weekly = _prepare_leave(
        data.leave,
        this_week_start=this_week_start,
    )

    # SQL Base satırları ActivityAssignment_Id seviyesinde korunur.
    row_key_columns = [
        "Resource_Id",
        "ActivityAssignment_Id",
        "Consultant_Name",
        "Level",
        "Job_Title",
        "Location",
        "Project_Name",
        "Project_Type",
        "Project_Status",
        "Assignment_Start",
        "Assignment_End",
    ]

    tracker = base[row_key_columns].drop_duplicates().copy()

    tracker = tracker.merge(
        submission_status,
        on="ActivityAssignment_Id",
        how="left",
    )

    tracker["Submission"] = (
        tracker["Submission"]
        .fillna("Inactive")
    )

    # Son tamamlanmış haftadan geriye doğru 52 hafta.
    weeks = [
        this_week_start - pd.Timedelta(weeks=week_number)
        for week_number in range(1, 53)
    ]

    time_lookup = time_entry_agg.copy()

    leave_lookup = leave_weekly.copy()

    for week_start in weeks:
        week_label = week_start.strftime("%Y-%m-%d")

        logged_column = f"Logged_Hours_{week_label}"
        leave_column = f"Leave_{week_label}"
        consumed_column = f"Consumed_Days_{week_label}"

        weekly_time = time_lookup.loc[
            time_lookup["WeekStart"].eq(week_start),
            [
                "ActivityAssignment_Id",
                "Logged_Hours",
                "Consumed_Days",
            ],
        ].copy()

        weekly_time = weekly_time.rename(
            columns={
                "Logged_Hours": logged_column,
                "Consumed_Days": consumed_column,
            }
        )

        tracker = tracker.merge(
            weekly_time,
            on="ActivityAssignment_Id",
            how="left",
        )

        weekly_leave = leave_lookup.loc[
            leave_lookup["WeekStart"].eq(week_start),
            [
                "Resource_Id",
                "Leave_Info",
            ],
        ].copy()

        weekly_leave = weekly_leave.rename(
            columns={
                "Leave_Info": leave_column,
            }
        )

        tracker = tracker.merge(
            weekly_leave,
            on="Resource_Id",
            how="left",
        )

        tracker[logged_column] = (
            pd.to_numeric(
                tracker[logged_column],
                errors="coerce",
            )
            .fillna(0.0)
        )

        tracker[consumed_column] = (
            pd.to_numeric(
                tracker[consumed_column],
                errors="coerce",
            )
            .fillna(0.0)
        )

        tracker[leave_column] = (
            tracker[leave_column]
            .fillna("0 hours")
            .astype(str)
        )

    # SQL SELECT kolon sırası.
    display_columns = [
        "Consultant_Name",
        "Level",
        "Job_Title",
        "Location",
        "Project_Name",
        "Project_Type",
        "Submission",
        "Project_Status",
        "Assignment_Start",
        "Assignment_End",
    ]

    # Haftalık kolonlar SQL'deki gibi hafta bazında iç içe sıralanır.
    weekly_columns: list[str] = []

    for week_start in weeks:
        week_label = week_start.strftime("%Y-%m-%d")

        weekly_columns.extend(
            [
                f"Logged_Hours_{week_label}",
                f"Leave_{week_label}",
                f"Consumed_Days_{week_label}",
            ]
        )

    # Timestamp yerine yalnızca tarih göster.
    for column in [
        "Assignment_Start",
        "Assignment_End",
    ]:
        tracker[column] = pd.to_datetime(
            tracker[column],
            errors="coerce",
        ).dt.date

    tracker = tracker[
        display_columns + weekly_columns
    ]

    tracker = tracker.sort_values(
        [
            "Consultant_Name",
            "Project_Name",
        ],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    return tracker