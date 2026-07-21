import json
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"

CACHE_INFO_PATH = OUTPUT_DIR / "cache_info.json"

REPORT_PATHS = {
    "Consultant Tracker": (
        OUTPUT_DIR / "consultant_tracker.parquet"
    ),
    "Project Tracker": (
        OUTPUT_DIR / "project_tracker.parquet"
    ),
    "Utilisation": (
        OUTPUT_DIR / "utilisation.parquet"
    ),
    "Utilisation Detailed": (
        OUTPUT_DIR / "utilisation_detailed.parquet"
    ),
    "Bench Status": (
        OUTPUT_DIR / "bench_status.parquet"
    ),
    "Partial Assignments": (
        OUTPUT_DIR / "partial_assignments.parquet"
    ),
}


st.set_page_config(
    page_title="HR Operations CLEARPEAKS",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def load_parquet(
    path: Path,
) -> pd.DataFrame:
    """
    Bir parquet raporunu yükler.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Report file not found:\n{path}\n\n"
            "Run the following command first:\n"
            "python refresh_data.py"
        )

    return pd.read_parquet(path)


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def load_all_reports() -> dict[str, pd.DataFrame]:
    """
    Dashboard ve chatbot için tüm raporları yükler.
    """

    reports = {}

    for report_name, report_path in REPORT_PATHS.items():
        if report_path.exists():
            reports[report_name] = pd.read_parquet(
                report_path
            )

    return reports


def load_cache_info() -> dict:
    """
    refresh_data.py tarafından oluşturulan cache bilgisini okur.
    """

    if not CACHE_INFO_PATH.exists():
        return {}

    try:
        with CACHE_INFO_PATH.open(
            "r",
            encoding="utf-8",
        ) as cache_file:
            return json.load(cache_file)

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return {}


def find_column(
    dataframe: pd.DataFrame,
    possible_names: list[str],
) -> str | None:
    """
    Farklı raporlardaki alternatif kolon isimlerini bulur.
    """

    for column_name in possible_names:
        if column_name in dataframe.columns:
            return column_name

    return None


def display_report_metrics(
    dataframe: pd.DataFrame,
    report_name: str,
) -> None:
    """
    Rapor türüne göre üst metrikleri gösterir.
    """

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Rows",
        f"{len(dataframe):,}",
    )

    metric_columns[1].metric(
        "Columns",
        f"{len(dataframe.columns):,}",
    )

    third_label = "Records"
    third_value = f"{len(dataframe):,}"

    fourth_label = "Status"
    fourth_value = "Available"

    if report_name == "Consultant Tracker":
        consultant_column = find_column(
            dataframe,
            [
                "Consultant Name",
                "Consultant_Name",
                "Resource name",
                "Resource_Name",
            ],
        )

        if consultant_column:
            third_label = "Consultants"
            third_value = (
                f"{dataframe[consultant_column].nunique():,}"
            )

        week_columns = [
            column
            for column in dataframe.columns
            if str(column).startswith("20")
        ]

        fourth_label = "Weekly Columns"
        fourth_value = f"{len(week_columns):,}"

    elif report_name == "Project Tracker":
        project_column = find_column(
            dataframe,
            [
                "Project Name",
                "Project_Name",
                "Client",
            ],
        )

        if project_column:
            third_label = "Projects"
            third_value = (
                f"{dataframe[project_column].nunique():,}"
            )

        consultant_column = find_column(
            dataframe,
            [
                "Consultant Name",
                "Consultant_Name",
                "Resource name",
            ],
        )

        if consultant_column:
            fourth_label = "Consultants"
            fourth_value = (
                f"{dataframe[consultant_column].nunique():,}"
            )

    elif report_name == "Utilisation":
        third_label = "Metrics"

        utilisation_column = find_column(
            dataframe,
            [
                "Utilisation",
                "Metric",
            ],
        )

        if utilisation_column:
            third_value = (
                f"{dataframe[utilisation_column].nunique():,}"
            )

        week_columns = [
            column
            for column in dataframe.columns
            if column != utilisation_column
        ]

        fourth_label = "Weeks"
        fourth_value = f"{len(week_columns):,}"

    elif report_name == "Utilisation Detailed":
        consultant_column = find_column(
            dataframe,
            [
                "Consultant Name",
                "Consultant_Name",
                "Resource name",
            ],
        )

        if consultant_column:
            third_label = "Consultants"
            third_value = (
                f"{dataframe[consultant_column].nunique():,}"
            )

        week_column = find_column(
            dataframe,
            [
                "WeekStart",
                "Week Start",
                "Week",
            ],
        )

        if week_column:
            fourth_label = "Weeks"
            fourth_value = (
                f"{dataframe[week_column].nunique():,}"
            )

    elif report_name == "Bench Status":
        consultant_column = find_column(
            dataframe,
            [
                "Resource name",
                "Consultant Name",
                "Consultant_Name",
            ],
        )

        if consultant_column:
            third_label = "Consultants on Bench"
            third_value = (
                f"{dataframe[consultant_column].nunique():,}"
            )

        weeks_column = find_column(
            dataframe,
            [
                "Number of weeks on bench since last assignment",
                "Weeks on bench",
            ],
        )

        if weeks_column and not dataframe.empty:
            maximum_weeks = pd.to_numeric(
                dataframe[weeks_column],
                errors="coerce",
            ).max()

            fourth_label = "Maximum Bench Weeks"
            fourth_value = (
                "-"
                if pd.isna(maximum_weeks)
                else f"{maximum_weeks:,.0f}"
            )

    elif report_name == "Partial Assignments":
        consultant_column = find_column(
            dataframe,
            [
                "Resource name",
                "Consultant Name",
                "Consultant_Name",
            ],
        )

        if consultant_column:
            third_label = "Consultants"
            third_value = (
                f"{dataframe[consultant_column].nunique():,}"
            )

        client_column = find_column(
            dataframe,
            [
                "Client",
                "Project Name",
                "Project_Name",
            ],
        )

        if client_column:
            fourth_label = "Clients / Projects"
            fourth_value = (
                f"{dataframe[client_column].nunique():,}"
            )

    metric_columns[2].metric(
        third_label,
        third_value,
    )

    metric_columns[3].metric(
        fourth_label,
        fourth_value,
    )


def display_filters(
    dataframe: pd.DataFrame,
    report_name: str,
) -> pd.DataFrame:
    """
    Rapor için uygun filtreleri üretir.
    """

    filtered_dataframe = dataframe.copy()

    searchable_columns = [
        column
        for column in filtered_dataframe.columns
        if (
            pd.api.types.is_object_dtype(
                filtered_dataframe[column]
            )
            or isinstance(
                filtered_dataframe[column].dtype,
                pd.StringDtype,
            )
        )
    ]

    with st.expander(
        "Filters",
        expanded=False,
    ):
        search_text = st.text_input(
            "Search report",
            key=f"search_{report_name}",
            placeholder=(
                "Search consultant, project, "
                "client, group or level..."
            ),
        )

        if search_text:
            search_mask = pd.Series(
                False,
                index=filtered_dataframe.index,
            )

            for column in searchable_columns:
                search_mask = (
                    search_mask
                    | filtered_dataframe[column]
                    .fillna("")
                    .astype(str)
                    .str.contains(
                        search_text,
                        case=False,
                        na=False,
                    )
                )

            filtered_dataframe = (
                filtered_dataframe.loc[
                    search_mask
                ]
            )

        filter_candidates = [
            "Group",
            "Level",
            "Client",
            "Project Name",
            "Project_Name",
            "Activity",
            "Project Status",
            "Project_Status",
        ]

        available_filter_columns = [
            column
            for column in filter_candidates
            if column in filtered_dataframe.columns
        ]

        if available_filter_columns:
            filter_columns = st.columns(
                min(
                    3,
                    len(available_filter_columns),
                )
            )

            for index, column in enumerate(
                available_filter_columns
            ):
                options = sorted(
                    filtered_dataframe[column]
                    .dropna()
                    .astype(str)
                    .loc[
                        lambda values: values.str.strip()
                        != ""
                    ]
                    .unique()
                    .tolist()
                )

                selected_values = filter_columns[
                    index % len(filter_columns)
                ].multiselect(
                    column,
                    options,
                    key=(
                        f"{report_name}_"
                        f"{column}_filter"
                    ),
                )

                if selected_values:
                    filtered_dataframe = (
                        filtered_dataframe.loc[
                            filtered_dataframe[
                                column
                            ]
                            .astype(str)
                            .isin(selected_values)
                        ]
                    )

    return filtered_dataframe


def display_standard_report(
    report_name: str,
) -> None:
    """
    Raporu filtreleme, kolon seçimi ve sayfalama ile gösterir.

    Büyük raporların tamamını tarayıcıya göndermediği için
    Streamlit MessageSizeError oluşmasını engeller.
    """

    st.subheader(report_name)

    report_path = REPORT_PATHS[report_name]

    try:
        dataframe = load_parquet(
            report_path
        )

        display_report_metrics(
            dataframe=dataframe,
            report_name=report_name,
        )

        st.divider()

        filtered_dataframe = display_filters(
            dataframe=dataframe,
            report_name=report_name,
        )

        if filtered_dataframe.empty:
            st.warning(
                "No records match the selected filters."
            )
            return

        all_columns = (
            filtered_dataframe.columns.tolist()
        )

        date_columns = [
            column
            for column in all_columns
            if str(column).startswith("20")
        ]

        non_date_columns = [
            column
            for column in all_columns
            if column not in date_columns
        ]

        if report_name == "Consultant Tracker":
            # Consultant Tracker çok geniş olduğu için başlangıçta
            # sadece temel kolonlar ve en yakın haftalar gösterilir.
            default_identity_columns = [
                column
                for column in [
                    "Resource ID",
                    "Resource_Id",
                    "Consultant Name",
                    "Consultant_Name",
                    "Resource name",
                    "Level",
                    "Group",
                    "Location",
                    "Client",
                    "Project Name",
                    "Project_Name",
                    "Expected availability date",
                    "Expected Availability Date",
                    "Number of active projects",
                ]
                if column in all_columns
            ]

            default_week_columns = (
                date_columns[:12]
            )

            default_columns = list(
                dict.fromkeys(
                    default_identity_columns
                    + default_week_columns
                )
            )

            if not default_columns:
                default_columns = (
                    all_columns[:20]
                )

        else:
            default_columns = (
                non_date_columns[:10]
                + date_columns[:12]
            )

            default_columns = list(
                dict.fromkeys(
                    default_columns
                )
            )

            if not default_columns:
                default_columns = (
                    all_columns[:20]
                )

        with st.expander(
            "Display settings",
            expanded=(
                report_name
                == "Consultant Tracker"
            ),
        ):
            selected_columns = st.multiselect(
                "Columns to display",
                options=all_columns,
                default=default_columns,
                key=f"{report_name}_columns",
            )

            rows_per_page = st.selectbox(
                "Rows per page",
                options=[
                    25,
                    50,
                    100,
                    200,
                    500,
                ],
                index=2,
                key=f"{report_name}_rows_per_page",
            )

        if not selected_columns:
            st.warning(
                "Select at least one column."
            )
            return

        total_rows = len(
            filtered_dataframe
        )

        total_pages = max(
            1,
            (
                total_rows
                + rows_per_page
                - 1
            )
            // rows_per_page,
        )

        page_number = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key=f"{report_name}_page",
        )

        start_row = (
            int(page_number) - 1
        ) * rows_per_page

        end_row = min(
            start_row + rows_per_page,
            total_rows,
        )

        page_dataframe = (
            filtered_dataframe
            .iloc[start_row:end_row]
            .loc[:, selected_columns]
            .copy()
        )

        st.caption(
            f"Showing rows "
            f"{start_row + 1:,}–{end_row:,} "
            f"of {total_rows:,} | "
            f"Page {int(page_number):,} "
            f"of {total_pages:,}"
        )

        st.dataframe(
            page_dataframe,
            use_container_width=True,
            hide_index=True,
            height=650,
        )

        st.caption(
            "The table is paginated to prevent "
            "large datasets from exceeding the "
            "Streamlit browser message limit."
        )

        csv_data = (
            filtered_dataframe
            .loc[:, selected_columns]
            .to_csv(index=False)
            .encode("utf-8-sig")
        )

        st.download_button(
            label="Download filtered data as CSV",
            data=csv_data,
            file_name=(
                report_name
                .lower()
                .replace(" ", "_")
                + ".csv"
            ),
            mime="text/csv",
            key=f"{report_name}_download",
        )

    except Exception as error:
        st.error(
            f"{report_name} could not be loaded."
        )

        st.exception(error)


def display_utilisation_report() -> None:
    """
    Utilisation raporunu tablo ve grafik olarak gösterir.
    """

    report_name = "Utilisation"

    st.subheader(report_name)

    try:
        dataframe = load_parquet(
            REPORT_PATHS[report_name]
        )

        display_report_metrics(
            dataframe=dataframe,
            report_name=report_name,
        )

        st.divider()

        utilisation_column = find_column(
            dataframe,
            [
                "Utilisation",
                "Metric",
            ],
        )

        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True,
        )

        if utilisation_column:
            week_columns = [
                column
                for column in dataframe.columns
                if column != utilisation_column
            ]

            chart_rows = [
                "Booked Capacity",
                "Maximum Capacity",
                "Forecasted Allocation",
            ]

            chart_dataframe = dataframe.loc[
                dataframe[
                    utilisation_column
                ].isin(chart_rows),
                [
                    utilisation_column,
                    *week_columns,
                ],
            ].copy()

            if not chart_dataframe.empty:
                chart_dataframe = (
                    chart_dataframe
                    .set_index(
                        utilisation_column
                    )
                    .transpose()
                )

                chart_dataframe = (
                    chart_dataframe
                    .apply(
                        pd.to_numeric,
                        errors="coerce",
                    )
                )

                st.subheader(
                    "Capacity Trend"
                )

                st.line_chart(
                    chart_dataframe,
                    use_container_width=True,
                )

        csv_data = (
            dataframe
            .to_csv(index=False)
            .encode("utf-8-sig")
        )

        st.download_button(
            label="Download utilisation as CSV",
            data=csv_data,
            file_name="utilisation.csv",
            mime="text/csv",
        )

    except Exception as error:
        st.error(
            "Utilisation report could not be loaded."
        )

        st.exception(error)


def display_chatbot_page() -> None:
    """
    Chatbot sayfasının veri kaynaklarını hazırlar.
    """

    st.subheader("HR Ops Data Chatbot")

    reports = load_all_reports()

    if not reports:
        st.error(
            "No report data was found. "
            "Run python refresh_data.py first."
        )
        return

    st.success(
        f"{len(reports)} report datasets "
        "are available for the chatbot."
    )

    available_report_names = list(
        reports.keys()
    )

    selected_report = st.selectbox(
        "Select a dataset",
        available_report_names,
    )

    selected_dataframe = reports[
        selected_report
    ]

    st.caption(
        f"{selected_report}: "
        f"{len(selected_dataframe):,} rows, "
        f"{len(selected_dataframe.columns):,} columns"
    )

    with st.expander(
        "View available columns",
        expanded=False,
    ):
        st.write(
            selected_dataframe.columns.tolist()
        )

    st.dataframe(
        selected_dataframe.head(20),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "The report datasets are now connected. "
        "The next step is to connect chatbot.py "
        "so questions are answered from these "
        "parquet reports only."
    )


st.title("HR Operations CLEARPEAKS")

cache_info = load_cache_info()

with st.sidebar:
    st.header("Navigation")

    page = st.radio(
        "Go to",
        [
            "Consultant Tracker",
            "Project Tracker",
            "Utilisation",
            "Utilisation Detailed",
            "Bench Status",
            "Partial Assignments",
            "Chatbot",
        ],
    )

    st.divider()
    st.subheader("Data Status")

    existing_reports = {
        report_name: report_path
        for report_name, report_path
        in REPORT_PATHS.items()
        if report_path.exists()
    }

    if len(existing_reports) == len(
        REPORT_PATHS
    ):
        st.success(
            "All reports available"
        )
    elif existing_reports:
        st.warning(
            f"{len(existing_reports)} of "
            f"{len(REPORT_PATHS)} reports available"
        )
    else:
        st.error(
            "No reports available"
        )

    if cache_info:
        last_refresh = cache_info.get(
            "last_refresh",
            cache_info.get(
                "generated_at",
                "Unknown",
            ),
        )

        duration = cache_info.get(
            "duration_seconds",
            "Unknown",
        )

        st.caption(
            f"Last refresh: {last_refresh}"
        )

        st.caption(
            f"Duration: {duration} sec"
        )

    else:
        st.caption(
            "No cache_info.json found."
        )

    for report_name, report_path in (
        REPORT_PATHS.items()
    ):
        status_icon = (
            "✅"
            if report_path.exists()
            else "❌"
        )

        st.caption(
            f"{status_icon} {report_name}"
        )

    st.divider()

    if st.button(
        "Clear app cache",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "To refresh report data run:"
    )

    st.code(
        "python refresh_data.py",
        language="powershell",
    )


if page == "Utilisation":
    display_utilisation_report()

elif page == "Chatbot":
    display_chatbot_page()

else:
    display_standard_report(
        page
    )