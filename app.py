import json
from pathlib import Path

import streamlit as st
import pandas as pd

CACHE_DIR = Path("data/cache")
CACHE_INFO_PATH = CACHE_DIR / "cache_info.json"

CONSULTANT_TRACKER_PATH = CACHE_DIR / "consultant_tracker.parquet"
PROJECT_TRACKER_PATH = CACHE_DIR / "project_tracker.parquet"


@st.cache_data(ttl=3600, show_spinner=False)
def load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python refresh_data.py")
    return pd.read_parquet(path)


def load_cache_info() -> dict:
    if not CACHE_INFO_PATH.exists():
        return {}

    with open(CACHE_INFO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


st.set_page_config(
    page_title="HR Operations CLEARPEAKS",
    page_icon="📊",
    layout="wide",
)

st.title("HR Operations CLEARPEAKS")

cache_info = load_cache_info()

with st.sidebar:
    st.header("Navigation")

    page = st.radio(
        "Go to",
        ["Consultant Tracker", "Project Tracker", "Chatbot"],
    )

    st.divider()
    st.subheader("Data Status")

    if cache_info:
        st.success(cache_info.get("status", "UNKNOWN"))
        st.caption(f"Last refresh: {cache_info.get('last_refresh')}")
        st.caption(f"Duration: {cache_info.get('duration_seconds')} sec")
        st.caption(f"Consultant rows: {cache_info.get('consultant_tracker_rows')}")
        st.caption(f"Project rows: {cache_info.get('project_tracker_rows')}")
        st.caption(f"Technologies: {cache_info.get('technologies')}")
        st.caption(f"Professional experience: {cache_info.get('professional_experience')}")
    else:
        st.warning("No cache info found. Run refresh_data.py first.")

    st.divider()

    if st.button("Clear app cache"):
        st.cache_data.clear()
        st.rerun()


if page == "Consultant Tracker":
    st.subheader("Consultant Tracker")

    try:
        df = load_parquet(CONSULTANT_TRACKER_PATH)

        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", len(df))
        c2.metric("Columns", len(df.columns))

        if "Consultant_Name" in df.columns:
            c3.metric("Consultants", df["Consultant_Name"].nunique())
        else:
            c3.metric("Consultants", "-")

        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error("Consultant Tracker could not be loaded.")
        st.exception(e)


elif page == "Project Tracker":
    st.subheader("Project Tracker")

    try:
        df = load_parquet(PROJECT_TRACKER_PATH)

        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", len(df))
        c2.metric("Columns", len(df.columns))

        if "Project_Name" in df.columns:
            c3.metric("Projects", df["Project_Name"].nunique())
        else:
            c3.metric("Projects", "-")

        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error("Project Tracker could not be loaded.")
        st.exception(e)


elif page == "Chatbot":
    st.subheader("HR Ops Data Chatbot")
    st.info("Next step: we will connect the HR planning engines here.")