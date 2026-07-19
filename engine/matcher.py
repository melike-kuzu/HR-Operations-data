import pandas as pd


def normalize_name(value):
    return str(value).strip().lower()


def find_name_column(df: pd.DataFrame):
    possible_cols = [
        "Consultant_Name",
        "Consultant Name",
        "Employee",
        "Employee_Name",
        "Employee Name",
        "Name",
        "Consultant",
        "Full Name",
    ]

    for col in possible_cols:
        if col in df.columns:
            return col

    return None


def intersect_consultants(left_df: pd.DataFrame, right_df: pd.DataFrame):
    if left_df.empty or right_df.empty:
        return pd.DataFrame()

    left_col = find_name_column(left_df)
    right_col = find_name_column(right_df)

    if not left_col or not right_col:
        return pd.DataFrame()

    left = left_df.copy()
    right = right_df.copy()

    left["_name_key"] = left[left_col].apply(normalize_name)
    right["_name_key"] = right[right_col].apply(normalize_name)

    merged = left.merge(
        right,
        on="_name_key",
        how="inner",
        suffixes=("_availability", "_profile"),
    )

    return merged.drop(columns=["_name_key"], errors="ignore")