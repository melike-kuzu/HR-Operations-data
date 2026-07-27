from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from workforce_assistant.repositories.report_registry import get_report_path


@lru_cache(maxsize=32)
def _read_parquet_cached(
    path_string: str,
    modified_timestamp_ns: int,
) -> pd.DataFrame:
    del modified_timestamp_ns
    return pd.read_parquet(path_string)


def load_report(report_name: str) -> pd.DataFrame:
    report_path: Path = get_report_path(report_name)

    if not report_path.is_file():
        raise FileNotFoundError(
            f"Report file was not found: {report_path}. "
            "Run 'python refresh_data.py' first."
        )

    dataframe = _read_parquet_cached(
        str(report_path),
        report_path.stat().st_mtime_ns,
    )
    return dataframe.copy()


def clear_report_cache() -> None:
    _read_parquet_cached.cache_clear()
