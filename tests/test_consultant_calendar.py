from pathlib import Path

from db import run_query_to_df
from engine.master_dataset import MasterData
from engine.reports.consultant_tracker import (
    build_consultant_calendar,
    build_consultant_tracker,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_sql(relative_path: str) -> str:
    """
    Proje köküne göre SQL dosyasını okur.
    """

    sql_path = PROJECT_ROOT / relative_path

    return sql_path.read_text(encoding="utf-8")


def load_master_data() -> MasterData:
    """
    Üç base SQL sorgusunu çalıştırıp MasterData oluşturur.
    """

    assignments = run_query_to_df(
        read_sql("sql/base/assignments.sql")
    )

    time_entries = run_query_to_df(
        read_sql("sql/base/weekly_time_entries.sql")
    )

    leave = run_query_to_df(
        read_sql("sql/base/weekly_leave.sql")
    )

    return MasterData(
        assignments=assignments,
        time_entries=time_entries,
        leave=leave,
    )


def test_consultant_tracker():
    """
    Consultant calendar ve tracker'ın doğru üretildiğini kontrol eder.
    """

    data = load_master_data()

    calendar = build_consultant_calendar(data)
    tracker = build_consultant_tracker(data)

    assert not calendar.empty, "Consultant calendar boş üretildi."
    assert not tracker.empty, "Consultant tracker boş üretildi."

    calendar_required_columns = {
        "Group",
        "Consultant_Name",
        "WeekStart",
        "CalendarValue",
    }

    assert calendar_required_columns.issubset(calendar.columns), (
        "Consultant calendar gerekli kolonları içermiyor. "
        f"Mevcut kolonlar: {calendar.columns.tolist()}"
    )

    tracker_required_columns = {
        "Group",
        "Consultant_Name",
        "Expected_Availability_Date",
        "Active_Projects",
    }

    assert tracker_required_columns.issubset(tracker.columns), (
        "Consultant tracker gerekli kolonları içermiyor. "
        f"Mevcut kolonlar: {tracker.columns.tolist()}"
    )

    print("\nCalendar shape:")
    print(calendar.shape)

    print("\nCalendar preview:")
    print(calendar.head())

    print("\nTracker shape:")
    print(tracker.shape)

    print("\nTracker preview:")
    print(tracker.head())

    print("\nTracker columns:")
    print(tracker.columns.tolist())


def test_consultant_tracker_has_one_row_per_consultant():
    data = load_master_data()

    tracker = build_consultant_tracker(data)

    consultant_count = (
        tracker[
            [
                "Group",
                "Consultant_Name",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    assert len(tracker) == consultant_count

    assert not tracker.duplicated(
        subset=[
            "Group",
            "Consultant_Name",
        ]
    ).any()

    assert len(tracker) < 10_000
    