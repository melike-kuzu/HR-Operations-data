import re
from datetime import datetime
import pandas as pd


def parse_date(text: str):
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"]:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def extract_dates(question: str):
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
    ]

    dates = []
    for pattern in patterns:
        for value in re.findall(pattern, question):
            parsed = parse_date(value)
            if parsed:
                dates.append(parsed.strftime("%Y-%m-%d"))

    return dates


def find_closest_week_column(target_date: str, df: pd.DataFrame):
    target = parse_date(target_date)
    if not target:
        return None

    candidates = []

    for col in df.columns:
        parsed = parse_date(str(col))
        if parsed:
            candidates.append((abs((parsed - target).days), str(col)))

    if not candidates:
        return None

    return sorted(candidates, key=lambda x: x[0])[0][1]


def get_bench_on_date(consultant_df: pd.DataFrame, target_date: str):
    week_col = find_closest_week_column(target_date, consultant_df)

    if not week_col:
        return pd.DataFrame()

    values = consultant_df[week_col].astype(str).str.upper().str.strip()
    mask = values.eq("B") | values.str.contains("BENCH", na=False)

    cols = [
        c for c in [
            "Team",
            "Consultant_Name",
            "Level",
            "Group",
            "Expected_Availability_Date",
            "Active_Project",
            week_col,
        ]
        if c in consultant_df.columns
    ]

    result = consultant_df.loc[mask, cols].copy()
    result["Matched_Week"] = week_col
    result["Reason"] = "Bench value found in Consultant Tracker"
    return result


def get_future_bench_from_date(consultant_df: pd.DataFrame, from_date: str):
    start = parse_date(from_date)
    if not start:
        return pd.DataFrame()

    week_cols = []

    for col in consultant_df.columns:
        parsed = parse_date(str(col))
        if parsed and parsed >= start:
            week_cols.append(str(col))

    rows = []

    for _, row in consultant_df.iterrows():
        for col in week_cols:
            value = str(row[col]).upper().strip()

            if value == "B" or "BENCH" in value:
                rows.append({
                    "Consultant_Name": row.get("Consultant_Name"),
                    "Team": row.get("Team"),
                    "Level": row.get("Level"),
                    "Group": row.get("Group"),
                    "Expected_Availability_Date": row.get("Expected_Availability_Date"),
                    "First_Bench_Week": col,
                    "Status": value,
                })
                break

    return pd.DataFrame(rows)