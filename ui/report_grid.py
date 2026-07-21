"""Interactive report grid and export helpers."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode


STATUS_SUFFIX = "__STATUS"


@st.cache_data(show_spinner=False)
def load_parquet_report(
    path_string: str,
    modified_timestamp: float,
) -> pd.DataFrame:
    """
    Load a parquet report.

    The modified timestamp is included in the cache key so regenerated
    reports are automatically reloaded.
    """

    del modified_timestamp

    path = Path(path_string)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report file was not found: {path}"
        )

    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def dataframe_to_excel(
    dataframe: pd.DataFrame,
    sheet_name: str,
) -> bytes:
    """Convert a dataframe into an in-memory Excel workbook."""

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        dataframe.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name[:31],
        )

        worksheet = writer.sheets[
            sheet_name[:31]
        ]

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = (
            worksheet.dimensions
        )

        for column_cells in worksheet.columns:
            values = [
                (
                    ""
                    if cell.value is None
                    else str(cell.value)
                )
                for cell in column_cells
            ]

            maximum_width = max(
                (
                    len(value)
                    for value in values
                ),
                default=0,
            )

            adjusted_width = min(
                max(
                    maximum_width + 2,
                    10,
                ),
                45,
            )

            column_letter = (
                column_cells[0].column_letter
            )

            worksheet.column_dimensions[
                column_letter
            ].width = adjusted_width

    return output.getvalue()


def _normalise_report_key(
    report_key: str,
) -> str:
    """Normalise report key for report-specific display rules."""

    return (
        report_key
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _is_status_column(
    column_name: object,
) -> bool:
    """Return True for hidden technical status columns."""

    return str(column_name).endswith(
        STATUS_SUFFIX
    )


def _is_week_column(
    column_name: object,
) -> bool:
    """Return True for YYYY-MM-DD calendar columns."""

    return bool(
        re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            str(column_name),
        )
    )


def _looks_like_date_column(
    column_name: object,
) -> bool:
    """
    Identify report columns which contain dates.

    This includes names such as:
        Assignment_Start
        Assignment_End
        Expected_Availability_Date
        Last Assignment End
        WeekStart
        Week_End
    """

    normalised_name = (
        str(column_name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    date_tokens = (
        "date",
        "start",
        "end",
        "weekstart",
        "week_start",
    )

    return any(
        token in normalised_name
        for token in date_tokens
    )


def _contains_python_dates(
    series: pd.Series,
) -> bool:
    """
    Return True when an object column contains Python date or
    datetime values.

    PyArrow can load date columns as object dtype. Without conversion,
    AG Grid may display these values as [object Object].
    """

    non_null_values = series.dropna()

    if non_null_values.empty:
        return False

    sample = non_null_values.head(25)

    return sample.map(
        lambda value: isinstance(
            value,
            (date, datetime, pd.Timestamp),
        )
    ).any()


def _format_date_series(
    series: pd.Series,
) -> pd.Series:
    """Convert a date-like series to YYYY-MM-DD strings."""

    converted = pd.to_datetime(
        series,
        errors="coerce",
    )

    formatted = converted.dt.strftime(
        "%Y-%m-%d"
    )

    formatted = formatted.astype(
        object
    )

    formatted.loc[
        converted.isna()
    ] = None

    return formatted


def _visible_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove technical status columns from exports.

    Status columns remain available in the grid data for Consultant
    Tracker cell colouring.
    """

    visible_columns = [
        column
        for column in dataframe.columns
        if not _is_status_column(column)
    ]

    return dataframe[
        visible_columns
    ].copy()


def _prepare_grid_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare values for AG Grid.

    This fixes Project Tracker date columns which otherwise appear as
    [object Object] when parquet returns Python date objects.
    """

    grid_dataframe = dataframe.copy()

    for column in grid_dataframe.columns:
        series = grid_dataframe[column]

        is_datetime_dtype = (
            pd.api.types.is_datetime64_any_dtype(
                series
            )
        )

        contains_python_dates = (
            series.dtype == object
            and _contains_python_dates(
                series
            )
        )

        named_like_date = (
            _looks_like_date_column(column)
        )

        if (
            is_datetime_dtype
            or contains_python_dates
            or named_like_date
        ):
            converted = pd.to_datetime(
                series,
                errors="coerce",
            )

            # Only replace a name-based candidate when at least one
            # valid date was found. This prevents ordinary text fields
            # containing words such as "start" from being erased.
            if (
                is_datetime_dtype
                or contains_python_dates
                or converted.notna().any()
            ):
                grid_dataframe[column] = (
                    _format_date_series(series)
                )

    grid_dataframe = grid_dataframe.where(
        pd.notna(grid_dataframe),
        None,
    )

    return grid_dataframe


def _prepare_export_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare a clean visible dataframe for CSV and Excel exports.

    Technical status fields are excluded and Python date objects are
    converted to simple YYYY-MM-DD values.
    """

    export_dataframe = _visible_dataframe(
        dataframe
    )

    for column in export_dataframe.columns:
        series = export_dataframe[column]

        if (
            pd.api.types.is_datetime64_any_dtype(
                series
            )
            or (
                series.dtype == object
                and _contains_python_dates(
                    series
                )
            )
        ):
            export_dataframe[column] = (
                _format_date_series(series)
            )

    return export_dataframe


def _calendar_cell_style(
    week_column: str,
) -> JsCode:
    """
    Preserve the existing Consultant Tracker calendar colours.
    """

    status_column = (
        f"{week_column}{STATUS_SUFFIX}"
    )

    return JsCode(
        f"""
        function(params) {{
            const statusField =
                {status_column!r};

            const rawStatus =
                params.data &&
                params.data[statusField] != null
                    ? String(
                        params.data[statusField]
                    )
                    : "";

            const status = rawStatus
                .trim()
                .toUpperCase()
                .replaceAll(" ", "_")
                .replaceAll("-", "_");

            const rawValue =
                params.value == null
                    ? ""
                    : String(params.value)
                        .trim()
                        .toUpperCase();

            const numericValue =
                Number.parseFloat(rawValue);

            const weekDate =
                new Date(
                    {week_column!r} + "T00:00:00"
                );

            const today = new Date();

            today.setHours(
                0,
                0,
                0,
                0
            );

            const currentDay =
                today.getDay();

            const daysFromMonday =
                currentDay === 0
                    ? 6
                    : currentDay - 1;

            const currentWeekStart =
                new Date(today);

            currentWeekStart.setDate(
                today.getDate()
                - daysFromMonday
            );

            const isFutureWeek =
                weekDate.getTime()
                > currentWeekStart.getTime();

            const isBench =
                status.includes("BENCH")
                || rawValue === "B";

            const isLeave =
                status.includes("LEAVE")
                || status.includes("HOLIDAY")
                || status.includes("ABSENCE")
                || rawValue === "L";

            const isPartial =
                status.includes("PART")
                || status.includes("PARTIAL")
                || status.includes("PARTLY")
                || (
                    !Number.isNaN(numericValue)
                    && numericValue > 0
                    && numericValue < 1
                );

            const isBooked =
                status.includes("BOOKED")
                || status.includes("ASSIGN")
                || status.includes("CONFIRMED")
                || (
                    !Number.isNaN(numericValue)
                    && numericValue >= 1
                );

            const isUnconfirmed =
                status.includes("UNCONFIRMED")
                || status.includes("FUTURE")
                || status.includes("EXPECTED");

            const baseStyle = {{
                textAlign: "center",
                fontWeight: "600",
                borderRight:
                    "1px solid rgba(49, 51, 63, 0.15)"
            }};

            if (isBench) {{
                return {{
                    ...baseStyle,
                    backgroundColor: "#C6EFCE",
                    color: "#006100"
                }};
            }}

            if (isLeave && isFutureWeek) {{
                return {{
                    ...baseStyle,
                    backgroundColor: "#F4CCCC",
                    color: "#741B47"
                }};
            }}

            if (isLeave) {{
                return {{
                    ...baseStyle,
                    backgroundColor: "#FFF2CC",
                    color: "#7F6000"
                }};
            }}

            if (
                isFutureWeek
                && (
                    isBooked
                    || isPartial
                    || isUnconfirmed
                )
            ) {{
                return {{
                    ...baseStyle,
                    backgroundColor: "#FCE5CD",
                    color: "#783F04"
                }};
            }}

            if (isPartial) {{
                return {{
                    ...baseStyle,
                    backgroundColor: "#F4CCCC",
                    color: "#990000"
                }};
            }}

            if (isBooked) {{
                return {{
                    ...baseStyle,
                    backgroundColor: "#E06666",
                    color: "#FFFFFF"
                }};
            }}

            return baseStyle;
        }}
        """
    )


def _general_report_row_style() -> JsCode:
    """
    Apply alternating white and light-grey rows to reports other than
    Consultant Tracker.
    """

    return JsCode(
        """
        function(params) {
            if (params.node.rowIndex % 2 === 0) {
                return {
                    backgroundColor: "#FFFFFF"
                };
            }

            return {
                backgroundColor: "#F3F5F7"
            };
        }
        """
    )


def _configure_default_columns(
    builder: GridOptionsBuilder,
) -> None:
    """Set Excel-like default column behaviour."""

    builder.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        editable=False,
        floatingFilter=True,
        suppressMenu=False,
        wrapHeaderText=True,
        autoHeaderHeight=True,
        minWidth=110,
    )


def _configure_status_columns(
    builder: GridOptionsBuilder,
    dataframe: pd.DataFrame,
) -> None:
    """Hide technical status columns from the displayed grid."""

    for column in dataframe.columns:
        if _is_status_column(column):
            builder.configure_column(
                str(column),
                hide=True,
                suppressColumnsToolPanel=True,
                filter=False,
                sortable=False,
            )


def _configure_consultant_tracker(
    builder: GridOptionsBuilder,
    dataframe: pd.DataFrame,
) -> None:
    """
    Preserve Consultant Tracker configuration and colouring.
    """

    pinned_columns = [
        "Group",
        "Consultant_Name",
        "Expected_Availability_Date",
        "Active_Projects",
    ]

    column_widths = {
        "Group": 150,
        "Consultant_Name": 220,
        "Expected_Availability_Date": 190,
        "Active_Projects": 145,
    }

    for column in pinned_columns:
        if column not in dataframe.columns:
            continue

        builder.configure_column(
            column,
            pinned="left",
            lockPinned=True,
            width=column_widths[column],
            minWidth=column_widths[column],
            filter=(
                "agNumberColumnFilter"
                if column == "Active_Projects"
                else "agTextColumnFilter"
            ),
        )

    for column in dataframe.columns:
        column_name = str(column)

        if not _is_week_column(
            column_name
        ):
            continue

        builder.configure_column(
            column_name,
            width=110,
            minWidth=100,
            maxWidth=135,
            filter="agTextColumnFilter",
            cellStyle=_calendar_cell_style(
                column_name
            ),
            headerClass="calendar-week-header",
        )


def _configure_general_report(
    builder: GridOptionsBuilder,
    dataframe: pd.DataFrame,
) -> None:
    """
    Configure Project Tracker and all other normal reports.

    The first useful identifying columns are pinned to the left.
    """

    preferred_pinned_columns = [
        "Consultant_Name",
        "Consultant Name",
        "Resource_Name",
        "Resource name",
        "Project_Name",
        "Project Name",
        "Client",
        "Group",
    ]

    pinned_count = 0

    for column in preferred_pinned_columns:
        if (
            column in dataframe.columns
            and pinned_count < 2
        ):
            builder.configure_column(
                column,
                pinned="left",
                lockPinned=True,
                minWidth=180,
            )

            pinned_count += 1

    for column in dataframe.columns:
        column_name = str(column)

        if _looks_like_date_column(
            column_name
        ):
            builder.configure_column(
                column_name,
                minWidth=135,
                filter="agTextColumnFilter",
            )


def _build_grid_options(
    dataframe: pd.DataFrame,
    report_key: str,
) -> dict:
    """Build AG Grid options for the selected report."""

    builder = GridOptionsBuilder.from_dataframe(
        dataframe
    )

    _configure_default_columns(
        builder
    )

    _configure_status_columns(
        builder,
        dataframe,
    )

    normalised_report_key = (
        _normalise_report_key(
            report_key
        )
    )

    is_consultant_tracker = (
        normalised_report_key
        == "consultant_tracker"
    )

    if is_consultant_tracker:
        _configure_consultant_tracker(
            builder,
            dataframe,
        )
    else:
        _configure_general_report(
            builder,
            dataframe,
        )

    grid_configuration = {
    "animateRows": False,
    "rowHeight": 34,
    "headerHeight": 42,
    "enableCellTextSelection": True,
    "ensureDomOrder": True,
    "suppressRowClickSelection": True,
    "suppressDragLeaveHidesColumns": True,
    "suppressColumnVirtualisation": False,
    "enableRangeSelection": True,
    "pagination": True,
    "paginationPageSize": 100,
    "paginationPageSizeSelector": [
        50,
        100,
        250,
        500,
    ],
    "sideBar": {
        "toolPanels": [
            {
                "id": "columns",
                "labelDefault": "Columns",
                "toolPanel": "agColumnsToolPanel",
            },
            {
                "id": "filters",
                "labelDefault": "Filters",
                "toolPanel": "agFiltersToolPanel",
            },
        ],
        "defaultToolPanel": None,
    },
}
    if not is_consultant_tracker:
        grid_configuration[
            "getRowStyle"
        ] = _general_report_row_style()

    builder.configure_grid_options(
        **grid_configuration
    )

    return builder.build()


def _render_grid_css(
    report_key: str,
) -> None:
    """
    Apply the ClearPeaks-style design to every report grid.

    All reports:
        - Turquoise column headers
        - White header text
        - Light-turquoise filter row
        - White and light-grey alternating rows
        - Light-turquoise hover colour

    Consultant Tracker calendar cell colours remain unchanged because
    those colours are controlled separately by _calendar_cell_style().
    """

    st.markdown(
        """
        <style>
        /* ---------------------------------------------------------
           GENERAL AG GRID SETTINGS
        --------------------------------------------------------- */

        .ag-theme-streamlit {
            --ag-font-size: 13px;
            --ag-row-height: 34px;
            --ag-header-height: 42px;

            --ag-header-background-color: #00AFC1;
            --ag-header-foreground-color: #FFFFFF;

            --ag-background-color: #FFFFFF;
            --ag-odd-row-background-color: #F3F5F7;

            --ag-row-hover-color: #DDF5F7;
            --ag-selected-row-background-color: #C9EEF1;

            --ag-border-color: #D9DEE3;
            --ag-row-border-color: #E5E9ED;
        }


        /* ---------------------------------------------------------
           COMPLETE HEADER AREA
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-header,
        .ag-theme-streamlit .ag-header-viewport,
        .ag-theme-streamlit .ag-header-container,
        .ag-theme-streamlit .ag-header-row,
        .ag-theme-streamlit .ag-pinned-left-header,
        .ag-theme-streamlit .ag-pinned-right-header {
            background-color: #00AFC1 !important;
        }


        /* ---------------------------------------------------------
           EVERY COLUMN HEADER
           Consultant Name, Location, Project Name, dates, etc.
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-header-cell,
        .ag-theme-streamlit .ag-header-group-cell {
            background-color: #00AFC1 !important;
            color: #FFFFFF !important;
            border-right: 1px solid rgba(
                255,
                255,
                255,
                0.30
            ) !important;
        }

        .ag-theme-streamlit .ag-header-cell-label,
        .ag-theme-streamlit .ag-header-group-cell-label {
            color: #FFFFFF !important;
        }

        .ag-theme-streamlit .ag-header-cell-text,
        .ag-theme-streamlit .ag-header-group-text {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }


        /* ---------------------------------------------------------
           HEADER ICONS
           Sort, menu and filter icons
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-header-icon,
        .ag-theme-streamlit .ag-sort-indicator-icon,
        .ag-theme-streamlit .ag-header-cell-menu-button,
        .ag-theme-streamlit .ag-header-cell-filter-button,
        .ag-theme-streamlit .ag-icon {
            color: #FFFFFF !important;
        }

        .ag-theme-streamlit .ag-header-cell-menu-button:hover,
        .ag-theme-streamlit .ag-header-cell-filter-button:hover {
            color: #FFFFFF !important;
            opacity: 1 !important;
        }


        /* ---------------------------------------------------------
           FILTER ROW
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-floating-filter,
        .ag-theme-streamlit .ag-floating-filter-body,
        .ag-theme-streamlit .ag-floating-filter-full-body {
            background-color: #DDF5F7 !important;
        }

        .ag-theme-streamlit .ag-floating-filter-input {
            background-color: #DDF5F7 !important;
        }

        .ag-theme-streamlit .ag-floating-filter-input input,
        .ag-theme-streamlit .ag-input-field-input,
        .ag-theme-streamlit .ag-text-field-input {
            background-color: #FFFFFF !important;
            color: #263238 !important;
            border: 1px solid #9DDDE3 !important;
            border-radius: 4px !important;
            padding-left: 6px !important;
        }

        .ag-theme-streamlit
        .ag-floating-filter-input
        input:focus {
            border-color: #00AFC1 !important;
            box-shadow: 0 0 0 1px #00AFC1 !important;
            outline: none !important;
        }


        /* ---------------------------------------------------------
           ZEBRA ROWS
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-row-even {
            background-color: #FFFFFF;
        }

        .ag-theme-streamlit .ag-row-odd {
            background-color: #F3F5F7;
        }


        /* ---------------------------------------------------------
           ROW HOVER
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-row-hover {
            background-color: #DDF5F7 !important;
        }


        /* ---------------------------------------------------------
           CELLS
        --------------------------------------------------------- */

        .ag-theme-streamlit .ag-cell {
            border-right: 1px solid #E5E9ED;
        }


        /* ---------------------------------------------------------
           CONSULTANT TRACKER WEEK HEADERS
        --------------------------------------------------------- */

        .ag-theme-streamlit
        .calendar-week-header
        .ag-header-cell-label {
            justify-content: center;
        }

        .ag-theme-streamlit
        .calendar-week-header {
            background-color: #00AFC1 !important;
            color: #FFFFFF !important;
        }


        /* ---------------------------------------------------------
           PINNED COLUMNS
        --------------------------------------------------------- */

        .ag-theme-streamlit
        .ag-pinned-left-header {
            border-right: 2px solid #008C9A !important;
        }

        .ag-theme-streamlit
        .ag-pinned-left-cols-container {
            border-right: 2px solid #C4DADD !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
#     


def render_report_grid(
    dataframe: pd.DataFrame,
    report_key: str,
) -> None:
    """
    Render an interactive report without changing its business content.
    """

    if dataframe.empty:
        st.info(
            "This report currently contains no rows."
        )
        return

    grid_dataframe = _prepare_grid_dataframe(
        dataframe
    )

    export_dataframe = _prepare_export_dataframe(
        dataframe
    )

    grid_options = _build_grid_options(
        dataframe=grid_dataframe,
        report_key=report_key,
    )

    _render_grid_css(
        report_key
    )

    AgGrid(
        grid_dataframe,
        gridOptions=grid_options,
        height=680,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        theme="streamlit",
        key=f"report_grid_{report_key}",
    )

    st.caption(
        (
            f"{len(export_dataframe):,} rows · "
            f"{len(export_dataframe.columns):,} columns"
        )
    )

    safe_filename = (
        report_key
        .replace("-", "_")
        .replace(" ", "_")
    )

    export_columns = st.columns(
        [1, 1, 4]
    )

    with export_columns[0]:
        csv_data = (
            export_dataframe
            .to_csv(index=False)
            .encode("utf-8-sig")
        )

        st.download_button(
            label="Export CSV",
            data=csv_data,
            file_name=f"{safe_filename}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_export_{safe_filename}",
        )

    with export_columns[1]:
        excel_state_key = (
            f"excel_data_{safe_filename}"
        )

        if st.button(
            "Prepare Excel",
            use_container_width=True,
            key=f"prepare_excel_{safe_filename}",
        ):
            with st.spinner(
                "Preparing Excel file..."
            ):
                st.session_state[
                    excel_state_key
                ] = dataframe_to_excel(
                    dataframe=export_dataframe,
                    sheet_name=safe_filename,
                )

        if excel_state_key in st.session_state:
            st.download_button(
                label="Download Excel",
                data=st.session_state[
                    excel_state_key
                ],
                file_name=f"{safe_filename}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
                key=f"excel_export_{safe_filename}",
            )