from pathlib import Path
from time import perf_counter
from typing import Callable

import pandas as pd

from db import run_query_to_df
from engine.master_dataset import MasterData
from engine.reports.consultant_tracker import (
    build_consultant_tracker,
)
from engine.reports.project_tracker import (
    build_project_tracker,
)
from engine.reports.utilisation import (
    build_utilisation,
    build_utilisation_detailed,
)
from engine.reports.bench_status import (
    build_bench_status,
)
from engine.reports.partial_assignments import (
    build_partial_assignments,
)


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_FOLDER = PROJECT_ROOT / "output"


def read_sql(relative_path: str) -> str:
    """
    Proje köküne göre SQL dosyasını okur.
    """

    sql_path = PROJECT_ROOT / relative_path

    if not sql_path.exists():
        raise FileNotFoundError(
            f"SQL dosyası bulunamadı: {sql_path}"
        )

    return sql_path.read_text(
        encoding="utf-8"
    )


def load_master_data() -> MasterData:
    """
    Üç temel SQL sorgusunu çalıştırır ve MasterData oluşturur.
    """

    print("\nLoading assignments...")

    assignments = run_query_to_df(
        read_sql(
            "sql/base/assignments.sql"
        )
    )

    print(
        f"  assignments: {len(assignments):,} rows"
    )

    print("\nLoading weekly time entries...")

    time_entries = run_query_to_df(
        read_sql(
            "sql/base/weekly_time_entries.sql"
        )
    )

    print(
        f"  time_entries: {len(time_entries):,} rows"
    )

    print("\nLoading weekly leave...")

    leave = run_query_to_df(
        read_sql(
            "sql/base/weekly_leave.sql"
        )
    )

    print(
        f"  leave: {len(leave):,} rows"
    )

    return MasterData(
        assignments=assignments,
        time_entries=time_entries,
        leave=leave,
    )


def save_report(
    report_name: str,
    dataframe: pd.DataFrame,
) -> Path:
    """
    Raporu output klasörüne parquet olarak kaydeder.
    """

    output_file = (
        OUTPUT_FOLDER
        / f"{report_name}.parquet"
    )

    dataframe.to_parquet(
        output_file,
        index=False,
    )

    return output_file


def generate_report(
    report_name: str,
    builder: Callable[
        [MasterData],
        pd.DataFrame,
    ],
    data: MasterData,
) -> None:
    """
    Raporu üretir ve parquet dosyasına kaydeder.
    """

    print(
        f"\nGenerating {report_name}..."
    )

    start_time = perf_counter()

    report = builder(data)

    if not isinstance(
        report,
        pd.DataFrame,
    ):
        raise TypeError(
            f"{report_name} builder bir pandas "
            f"DataFrame döndürmedi."
        )

    output_file = save_report(
        report_name=report_name,
        dataframe=report,
    )

    elapsed = (
        perf_counter()
        - start_time
    )

    print(
        f"✓ {report_name:<25}"
        f"{len(report):>8,} rows   "
        f"{elapsed:>7.2f}s"
    )

    print(
        f"  Saved -> {output_file}"
    )


def main() -> None:
    """
    Tüm kaynak verileri bir kez yükler ve bütün raporları üretir.
    """

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("HR Reporting Platform - Data Refresh")
    print("=" * 70)

    total_start = perf_counter()

    print("\nLoading master datasets...")

    master_start = perf_counter()

    data = load_master_data()

    master_elapsed = (
        perf_counter()
        - master_start
    )

    print(
        f"\nMaster data loaded in "
        f"{master_elapsed:.2f} seconds"
    )

    print("\nMaster data summary:")

    for key, value in data.summary().items():
        print(
            f"  {key}: {value:,}"
        )

    reports = [
        (
            "consultant_tracker",
            build_consultant_tracker,
        ),
        (
            "project_tracker",
            build_project_tracker,
        ),
        (
            "utilisation",
            build_utilisation,
        ),
        (
            "utilisation_detailed",
            build_utilisation_detailed,
        ),
        (
            "bench_status",
            build_bench_status,
        ),
        (
            "partial_assignments",
            build_partial_assignments,
        ),
    ]

    successful_reports = []
    failed_reports = []

    for report_name, builder in reports:
        try:
            generate_report(
                report_name=report_name,
                builder=builder,
                data=data,
            )

            successful_reports.append(
                report_name
            )

        except Exception as error:
            failed_reports.append(
                (
                    report_name,
                    str(error),
                )
            )

            print(
                f"\n✗ {report_name} failed"
            )

            print(
                f"  Error: {error}"
            )

    total_elapsed = (
        perf_counter()
        - total_start
    )

    print("\n" + "=" * 70)
    print("Refresh summary")
    print("=" * 70)

    print(
        f"Successful reports: "
        f"{len(successful_reports)}"
    )

    for report_name in successful_reports:
        print(
            f"  ✓ {report_name}"
        )

    if failed_reports:
        print(
            f"\nFailed reports: "
            f"{len(failed_reports)}"
        )

        for report_name, error in failed_reports:
            print(
                f"  ✗ {report_name}: {error}"
            )

    print(
        f"\nTotal duration: "
        f"{total_elapsed:.2f} seconds"
    )

    print(
        f"Output folder: "
        f"{OUTPUT_FOLDER}"
    )

    print("=" * 70)

    if failed_reports:
        raise RuntimeError(
            f"{len(failed_reports)} report "
            f"could not be generated."
        )


if __name__ == "__main__":
    main()