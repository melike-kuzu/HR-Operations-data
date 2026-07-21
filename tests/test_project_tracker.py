import pytest

from tests.test_utilisation import load_master_data

from engine.reports.project_tracker import (
    build_project_tracker,
    build_project_tracker_base,
    build_project_tracker_base_with_submission,
)


@pytest.fixture(scope="module")
def master_data():
    """
    Veritabanından MasterData'yı yalnızca bir kez yükler.
    Bütün testler aynı veriyi kullanır.
    """
    return load_master_data()


def test_project_tracker_base(master_data):

    df = build_project_tracker_base(master_data)

    assert not df.empty

    expected_columns = [
        "Consultant_Name",
        "Project_Name",
        "Project_Type",
        "Project_Status",
        "Assignment_Start",
        "Assignment_End",
        "WeekStart",
        "Logged_Hours",
        "Consumed_Days",
        "Capacity",
        "Leave_Hours",
    ]

    for column in expected_columns:
        assert column in df.columns, (
            f"Eksik kolon: {column}"
        )


def test_project_tracker_submission(master_data):

    df = build_project_tracker_base_with_submission(
        master_data,
        run_date="2026-07-20",
    )

    assert not df.empty

    assert "Submission" in df.columns

    assert set(
        df["Submission"].dropna().unique()
    ).issubset(
        {
            "Active",
            "Inactive",
        }
    )

    last_week_start = "2026-07-13"

    active_assignments = (
        df.loc[
            (
                df["WeekStart"].eq(last_week_start)
                & df["Logged_Hours"].gt(0)
            ),
            [
                "Resource_Id",
                "ActivityAssignment_Id",
            ],
        ]
        .drop_duplicates()
    )

    for row in active_assignments.itertuples(
        index=False
    ):
        assignment_rows = df.loc[
            (
                df["Resource_Id"].eq(
                    row.Resource_Id
                )
                & df[
                    "ActivityAssignment_Id"
                ].eq(
                    row.ActivityAssignment_Id
                )
            )
        ]

        assert (
            assignment_rows["Submission"]
            .eq("Active")
            .all()
        )


def test_project_tracker(master_data):

    tracker = build_project_tracker(
        data=master_data,
        run_date="2026-07-20",
        number_of_weeks=52,
    )

    assert not tracker.empty

    required_columns = [
        "Consultant_Name",
        "Project_Name",
        "Project_Type",
        "Submission",
        "Project_Status",
        "Assignment_Start",
        "Assignment_End",
    ]

    for column in required_columns:
        assert column in tracker.columns, (
            f"Eksik kolon: {column}"
        )

    logged_hour_columns = [
        column
        for column in tracker.columns
        if column.startswith("Logged_Hours_")
    ]

    leave_columns = [
        column
        for column in tracker.columns
        if column.startswith("Leave_")
    ]

    consumed_day_columns = [
        column
        for column in tracker.columns
        if column.startswith("Consumed_Days_")
    ]

    assert len(logged_hour_columns) == 52
    assert len(leave_columns) == 52
    assert len(consumed_day_columns) == 52

    assert (
        "Logged_Hours_2026-07-13"
        in tracker.columns
    )

    assert (
        "Leave_2026-07-13"
        in tracker.columns
    )

    assert (
        "Consumed_Days_2026-07-13"
        in tracker.columns
    )

    print(
        tracker[
            required_columns
            + logged_hour_columns[-3:]
        ].head(10)
    )