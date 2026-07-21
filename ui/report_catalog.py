"""Report catalogue and parquet file discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ReportDefinition:
    """Metadata describing one official HR report."""

    key: str
    title: str
    description: str
    filename: str
    symbol: str


REPORTS: tuple[ReportDefinition, ...] = (
    ReportDefinition(
        key="consultant-tracker",
        title="Consultant Tracker",
        description=(
            "Weekly consultant allocation, availability, leave, bench "
            "and project assignment information."
        ),
        filename="consultant_tracker.parquet",
        symbol="CT",
    ),
    ReportDefinition(
        key="project-tracker",
        title="Project Tracker",
        description=(
            "Project-level staffing, client, assignment and delivery "
            "planning information."
        ),
        filename="project_tracker.parquet",
        symbol="PT",
    ),
    ReportDefinition(
        key="utilisation",
        title="Utilisation",
        description=(
            "Weekly workforce capacity, booked allocation and forecast "
            "utilisation summary."
        ),
        filename="utilisation.parquet",
        symbol="UT",
    ),
    ReportDefinition(
        key="utilisation-detailed",
        title="Utilisation Detailed",
        description=(
            "Detailed utilisation information supporting workforce "
            "planning and allocation decisions."
        ),
        filename="utilisation_detailed.parquet",
        symbol="UD",
    ),
    ReportDefinition(
        key="bench-status",
        title="Bench Status",
        description=(
            "Current bench population, level, group and possible next "
            "assignment information."
        ),
        filename="bench_status.parquet",
        symbol="BS",
    ),
    ReportDefinition(
        key="partial-assignments",
        title="Partial Assignments",
        description=(
            "Consultants assigned below full billable capacity, including "
            "client and allocation duration."
        ),
        filename="partial_assignments.parquet",
        symbol="PA",
    ),
)


def get_report(report_key: str) -> ReportDefinition | None:
    """Return a report definition using its URL key."""

    normalized_key = report_key.strip().lower()

    for report in REPORTS:
        if report.key == normalized_key:
            return report

    return None


def find_report_file(filename: str) -> Path | None:
    """
    Locate a generated parquet report.

    The search supports common output folders so the existing report
    generation pipeline does not need to be changed.
    """

    preferred_locations = (
        PROJECT_ROOT / "reports" / filename,
        PROJECT_ROOT / "data" / "reports" / filename,
        PROJECT_ROOT / "data" / "output" / filename,
        PROJECT_ROOT / "data" / "outputs" / filename,
        PROJECT_ROOT / "outputs" / filename,
        PROJECT_ROOT / "output" / filename,
        PROJECT_ROOT / filename,
    )

    for path in preferred_locations:
        if path.is_file():
            return path

    ignored_directories = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
    }

    for candidate in PROJECT_ROOT.rglob(filename):
        if any(part in ignored_directories for part in candidate.parts):
            continue

        if candidate.is_file():
            return candidate

    return None