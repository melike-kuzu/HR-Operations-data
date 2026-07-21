"""Interactive report grid and export helpers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


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
        raise FileNotFoundError(f"Report file was not found: {path}")

    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def dataframe_to_excel(
    dataframe: pd.DataFrame,
    sheet_name: str,
) -> bytes:
    """Convert a dataframe into an in-memory Excel workbook."""

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name[:31],
        )

        worksheet = writer.sheets[sheet_name[:31]]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:
            values = [
                "" if cell.value is None else str(cell.value)
                for cell in column_cells
            ]

            maximum_width = max(
                (len(value) for value in values),
                default=0,
            )

            adjusted_width = min(max(maximum_width + 2, 10), 45)
            worksheet.column_dimensions[column_cells[0].column_letter].width = (
                adjusted_width
            )

    return output.getvalue()


def render_report_grid(
    dataframe: pd.DataFrame,
    report_key: str,
) -> None:
    """Render the official report without changing its business content."""

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
        height=680,
    )

    st.caption(
        f"{len(dataframe):,} rows · {len(dataframe.columns):,} columns"
    )

    safe_filename = report_key.replace("-", "_")

    csv_data = dataframe.to_csv(index=False).encode("utf-8-sig")
    excel_data = dataframe_to_excel(
        dataframe=dataframe,
        sheet_name=safe_filename,
    )

    export_columns = st.columns([1, 1, 4])

    with export_columns[0]:
        st.download_button(
            label="Export CSV",
            data=csv_data,
            file_name=f"{safe_filename}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with export_columns[1]:
        st.download_button(
            label="Export Excel",
            data=excel_data,
            file_name=f"{safe_filename}.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )