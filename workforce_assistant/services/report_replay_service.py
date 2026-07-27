from __future__ import annotations

from typing import Any

import pandas as pd

from workforce_assistant.repositories.parquet_repository import (
    load_report,
)


class ReportReplayService:
    """Recreate supporting tables from saved message metadata."""

    def replay(
        self,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        if not metadata.get("replay_supported"):
            return pd.DataFrame()

        report_name = metadata.get("report_name")

        if not isinstance(report_name, str):
            return pd.DataFrame()

        if not report_name.strip():
            return pd.DataFrame()

        dataframe = load_report(
            report_name.strip()
        )

        filters = metadata.get(
            "filters",
            {},
        )

        if not isinstance(filters, dict):
            filters = {}

        if report_name == "technologies":
            dataframe = self._apply_technology_filters(
                dataframe,
                filters,
            )

        return dataframe

    @staticmethod
    def _apply_technology_filters(
        dataframe: pd.DataFrame,
        filters: dict[str, Any],
    ) -> pd.DataFrame:
        result = dataframe.copy()

        search_terms = filters.get(
            "search_terms",
            [],
        )

        if (
            isinstance(search_terms, list)
            and search_terms
            and "TechnologyName" in result.columns
        ):
            technology_values = (
                result["TechnologyName"]
                .astype("string")
                .str.lower()
                .fillna("")
            )

            technology_mask = pd.Series(
                False,
                index=result.index,
            )

            for term in search_terms:
                cleaned_term = str(
                    term
                ).strip().lower()

                if cleaned_term:
                    technology_mask |= (
                        technology_values.str.contains(
                            cleaned_term,
                            regex=False,
                            na=False,
                        )
                    )

            result = result.loc[
                technology_mask
            ].copy()

        if (
            filters.get(
                "exclude_no_knowledge"
            )
            and "Level.1" in result.columns
        ):
            knowledge_level = (
                result["Level.1"]
                .astype("string")
                .str.strip()
                .str.lower()
            )

            result = result.loc[
                knowledge_level.ne("no knowledge")
                & knowledge_level.notna()
            ].copy()

        if (
            filters.get(
                "current_employees_only"
            )
            and "Status" in result.columns
        ):
            current_status = (
                result["Status"]
                .astype("string")
                .str.strip()
                .str.lower()
            )

            result = result.loc[
                current_status.eq("current")
            ].copy()

        output_columns = [
            column
            for column in [
                "EmployeeName",
                "Level",
                "TechnologyName",
                "Vendor",
                "Priority",
                "Level.1",
                "LevelShort (stars)",
                "Type",
                "Manager",
                "Office",
                "UpdateDate",
            ]
            if column in result.columns
        ]

        if output_columns:
            result = result[
                output_columns
            ].copy()

        result = result.drop_duplicates()

        sort_columns = [
            column
            for column in [
                "EmployeeName",
                "TechnologyName",
            ]
            if column in result.columns
        ]

        if sort_columns:
            result = result.sort_values(
                sort_columns
            )

        return result