from pathlib import Path

from db import run_query_to_df
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

print(data.summary())

print("\nAssignments:")
print(data.assignments.head())

print("\nTime entries:")
print(data.time_entries.head())

print("\nLeave:")
print(data.leave.head())