from __future__ import annotations

from pathlib import Path

from workforce_assistant.config.settings import (
    PROJECT_ROOT,
    settings,
)


CACHE_DIR = PROJECT_ROOT / "data" / "cache"


REPORT_PATHS: dict[str, Path] = {
    # Generated operational reports
    "bench_status": settings.output_dir / "bench_status.parquet",
    "consultant_tracker": (
        settings.output_dir / "consultant_tracker.parquet"
    ),
    "partial_assignments": (
        settings.output_dir / "partial_assignments.parquet"
    ),
    "project_tracker": (
        settings.output_dir / "project_tracker.parquet"
    ),
    "utilisation": (
        settings.output_dir / "utilisation.parquet"
    ),
    "utilisation_detailed": (
        settings.output_dir / "utilisation_detailed.parquet"
    ),

    # Cached profile/search datasets
    "employee_list": CACHE_DIR / "employee_list.parquet",
    "languages": CACHE_DIR / "languages.parquet",
    "professional_experience": (
        CACHE_DIR / "professional_experience.parquet"
    ),
    "technologies": CACHE_DIR / "technologies.parquet",
}


def get_report_path(report_name: str) -> Path:
    normalised_name = report_name.strip().lower()

    try:
        return REPORT_PATHS[normalised_name]
    except KeyError as error:
        available_reports = ", ".join(
            sorted(REPORT_PATHS)
        )

        raise KeyError(
            f"Unknown report: {report_name}. "
            f"Available reports: {available_reports}"
        ) from error