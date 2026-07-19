import pandas as pd


def detect_experience_keyword(question: str):
    keywords = [
        "banking", "finance", "insurance", "retail", "telecom", "pharma",
        "healthcare", "energy", "customer", "migration", "cloud",
        "data warehouse", "manufacturing", "public sector", "allianz"
    ]

    q = question.lower()

    for keyword in keywords:
        if keyword in q:
            return keyword

    return None


def find_experience_matches(experience_df: pd.DataFrame, keyword: str):
    if experience_df.empty or not keyword:
        return pd.DataFrame()

    text_df = experience_df.astype(str).fillna("")

    mask = text_df.apply(
        lambda row: row.str.lower().str.contains(keyword.lower(), na=False).any(),
        axis=1,
    )

    return experience_df[mask].copy()