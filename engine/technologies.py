import pandas as pd


def detect_skill(question: str):
    skills = [
        "aws", "azure", "python", "sql", "power bi", "tableau", "databricks",
        "snowflake", "java", "sap", "oracle", "dbt", "spark",
        "machine learning", "ai", "genai", "data engineering"
    ]

    q = question.lower()

    for skill in skills:
        if skill in q:
            return skill

    return None


def detect_level(question: str):
    q = question.lower()

    if "expert" in q:
        return ["expert"]
    if "advanced" in q:
        return ["advanced", "expert"]
    if "intermediate" in q:
        return ["intermediate", "advanced", "expert"]
    if "basic" in q:
        return ["basic", "intermediate", "advanced", "expert"]

    return ["advanced", "expert"]


def find_technology_matches(technologies_df: pd.DataFrame, technology: str, levels):
    if technologies_df.empty or not technology:
        return pd.DataFrame()

    text_df = technologies_df.astype(str).fillna("")

    tech_mask = text_df.apply(
        lambda row: row.str.lower().str.contains(technology.lower(), na=False).any(),
        axis=1,
    )

    level_mask = text_df.apply(
        lambda row: row.str.lower().apply(
            lambda x: any(level in x for level in levels)
        ).any(),
        axis=1,
    )

    return technologies_df[tech_mask & level_mask].copy()