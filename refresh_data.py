from pathlib import Path
from datetime import datetime
import json
import time

import pandas as pd

from db import run_query_to_df

CONSULTANT_TRACKER_SQL_PATH = "consultant_tracker_2.sql"
PROJECT_TRACKER_SQL_PATH = "project_tracker_1.sql"
PROFILE_GENERATOR_PATH = "data/profile_generator.xlsx"

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def read_sql_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_sql_outputs():
    print("Running Consultant Tracker SQL...", flush=True)
    consultant_df = run_query_to_df(read_sql_file(CONSULTANT_TRACKER_SQL_PATH))
    consultant_df.to_parquet(CACHE_DIR / "consultant_tracker.parquet", index=False)
    print("Saved consultant_tracker:", consultant_df.shape, flush=True)

    print("Running Project Tracker SQL...", flush=True)
    project_df = run_query_to_df(read_sql_file(PROJECT_TRACKER_SQL_PATH))
    project_df.to_parquet(CACHE_DIR / "project_tracker.parquet", index=False)
    print("Saved project_tracker:", project_df.shape, flush=True)

    return consultant_df, project_df


def save_profile_outputs():
    print("Reading profile_generator.xlsx...", flush=True)
    sheets = pd.read_excel(PROFILE_GENERATOR_PATH, sheet_name=None)

    sheet_map = {
        "Technologies DB": "technologies.parquet",
        "Professional experience DB": "professional_experience.parquet",
        "Technical Expertise DB": "technical_expertise.parquet",
        "Business Expertise DB": "business_expertise.parquet",
        "Languages DB": "languages.parquet",
        "Certifications DB": "certifications.parquet",
        "Employee list": "employee_list.parquet",
    }

    profile_counts = {}

    for sheet_name, file_name in sheet_map.items():
        if sheet_name not in sheets:
            print(f"Skipped missing sheet: {sheet_name}", flush=True)
            profile_counts[file_name.replace(".parquet", "")] = 0
            continue

        df = sheets[sheet_name].dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.astype(str).replace("nan", "")

        df.to_parquet(CACHE_DIR / file_name, index=False)
        profile_counts[file_name.replace(".parquet", "")] = len(df)

        print(f"Saved {file_name}: {df.shape}", flush=True)

    return profile_counts


def save_cache_info(consultant_df, project_df, profile_counts, duration_seconds):
    cache_info = {
        "status": "SUCCESS",
        "last_refresh": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(duration_seconds, 2),
        "consultant_tracker_rows": len(consultant_df),
        "consultant_tracker_columns": len(consultant_df.columns),
        "project_tracker_rows": len(project_df),
        "project_tracker_columns": len(project_df.columns),
        **profile_counts,
    }

    with open(CACHE_DIR / "cache_info.json", "w", encoding="utf-8") as f:
        json.dump(cache_info, f, indent=4)

    print("Saved cache_info.json", flush=True)


if __name__ == "__main__":
    start = time.time()

    consultant_df, project_df = save_sql_outputs()
    profile_counts = save_profile_outputs()

    duration = time.time() - start
    save_cache_info(consultant_df, project_df, profile_counts, duration)

    print("Refresh complete.", flush=True)