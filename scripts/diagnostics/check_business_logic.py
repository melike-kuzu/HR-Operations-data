from pathlib import Path

from db import run_query_to_df
from engine.business_logic import (
    build_consultant_calendar_base,
)
from engine.master_dataset import MasterData


def read_sql(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


assignments_df = run_query_to_df(
    read_sql("sql/base/assignments.sql")
)

time_entries_df = run_query_to_df(
    read_sql("sql/base/weekly_time_entries.sql")
)

leave_df = run_query_to_df(
    read_sql("sql/base/weekly_leave.sql")
)

data = MasterData(
    assignments=assignments_df,
    time_entries=time_entries_df,
    leave=leave_df,
)

calendar = build_consultant_calendar_base(data)

print(calendar.head(20))

print("\nStatus counts:")
print(calendar["CalendarStatus"].value_counts())

print("\nInvalid duplicate consultant-week rows:")
duplicates = calendar.duplicated(
    subset=[
        "Resource_Id",
        "WeekStart",
    ],
    keep=False,
)

print(calendar.loc[duplicates])

print("\nCapacity outside 0-1:")
invalid_capacity = calendar.loc[
    (calendar["CalendarCapacity"] < 0)
    | (calendar["CalendarCapacity"] > 1)
]

print(invalid_capacity)