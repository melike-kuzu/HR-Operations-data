from pathlib import Path
import pandas as pd
import streamlit as st

from engine.availability import (
    extract_dates,
    get_bench_on_date,
    get_future_bench_from_date,
)

from engine.technologies import (
    detect_skill,
    detect_level,
    find_technology_matches,
)

from engine.experience import (
    detect_experience_keyword,
    find_experience_matches,
)

from engine.matcher import intersect_consultants

CACHE_DIR = Path("data/cache")


@st.cache_data(ttl=3600, show_spinner=False)
def load_parquet(name: str):
    path = CACHE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python refresh_data.py")
    return pd.read_parquet(path)


def load_consultant_tracker():
    return load_parquet("consultant_tracker.parquet")


def load_project_tracker():
    return load_parquet("project_tracker.parquet")


def load_technologies():
    return load_parquet("technologies.parquet")


def load_professional_experience():
    return load_parquet("professional_experience.parquet")


def ask_data_question(question: str) -> dict:
    consultant_df = load_consultant_tracker()
    technologies_df = load_technologies()
    experience_df_source = load_professional_experience()

    dates = extract_dates(question)
    skill = detect_skill(question)
    levels = detect_level(question)
    experience_keyword = detect_experience_keyword(question)

    q = question.lower()

    tables = {}
    answer_lines = []

    availability_df = pd.DataFrame()
    skill_df = pd.DataFrame()
    experience_df = pd.DataFrame()
    final_df = pd.DataFrame()

    if dates and any(x in q for x in ["bench", "available", "availability"]):
        target_date = dates[0]

        availability_df = get_bench_on_date(consultant_df, target_date)

        if availability_df.empty:
            availability_df = get_future_bench_from_date(consultant_df, target_date)

        tables["availability_matches"] = availability_df

        answer_lines.append(
            f"I checked Consultant Tracker for bench/availability around {target_date}."
        )

    if skill:
        skill_df = find_technology_matches(technologies_df, skill, levels)
        tables["technology_matches"] = skill_df

        answer_lines.append(
            f"I checked Technologies DB for {skill.upper()} with levels: {', '.join(levels)}."
        )

    if experience_keyword:
        experience_df = find_experience_matches(experience_df_source, experience_keyword)
        tables["experience_matches"] = experience_df

        answer_lines.append(
            f"I checked Professional Experience DB for '{experience_keyword}'."
        )

    if not availability_df.empty and not skill_df.empty:
        final_df = intersect_consultants(availability_df, skill_df)
        tables["final_availability_skill_matches"] = final_df

    if not final_df.empty and not experience_df.empty:
        final_df = intersect_consultants(final_df, experience_df)
        tables["final_availability_skill_experience_matches"] = final_df

    if not final_df.empty:
        answer_lines.append(f"Found {len(final_df)} consultant(s) matching the combined criteria.")
    elif not availability_df.empty and skill_df.empty and experience_df.empty:
        answer_lines.append(f"Found {len(availability_df)} availability match(es).")
    elif not skill_df.empty and availability_df.empty and experience_df.empty:
        answer_lines.append(f"Found {len(skill_df)} technology match(es).")
    elif not experience_df.empty and availability_df.empty and skill_df.empty:
        answer_lines.append(f"Found {len(experience_df)} experience match(es).")
    elif not availability_df.empty:
        answer_lines.append(
            f"Found {len(availability_df)} availability match(es), but no confirmed technology/experience match."
        )
    else:
        answer_lines.append("No clear matching consultants found in the cached data.")

    return {
        "answer": "\n\n".join(answer_lines),
        "tables": tables,
    }