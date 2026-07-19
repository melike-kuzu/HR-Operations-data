from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MasterData:
    """
    Dashboard ve chatbot tarafından kullanılan ortak veri kaynakları.

    assignments:
        Consultant, project ve assignment bilgileri.

    time_entries:
        Activity assignment bazında haftalık girilen saatler.

    leave:
        Resource bazında haftalık izin bilgileri.
    """

    assignments: pd.DataFrame
    time_entries: pd.DataFrame
    leave: pd.DataFrame

    def __post_init__(self) -> None:
        """
        MasterData oluşturulduğunda veri yapılarını kontrol eder
        ve tarih kolonlarını standart hale getirir.
        """

        self.assignments = self.assignments.copy()
        self.time_entries = self.time_entries.copy()
        self.leave = self.leave.copy()

        self._validate_required_columns()
        self._normalise_assignments()
        self._normalise_time_entries()
        self._normalise_leave()

    def _validate_required_columns(self) -> None:
        assignment_columns = {
            "Resource_Id",
            "ActivityAssignment_Id",
            "Consultant_Name",
            "Level",
            "Group",
            "Project_Name",
            "Assignment_Start",
            "Assignment_End",
            "Is_Active_Assignment",
        }

        time_entry_columns = {
            "ActivityAssignment_Id",
            "WeekStart",
            "Logged_Hours",
            "Consumed_Days",
            "Capacity",
        }

        leave_columns = {
            "Resource_Id",
            "WeekStart",
            "Leave_Hours",
            "Leave_Info",
        }

        self._check_columns(
            dataframe=self.assignments,
            required_columns=assignment_columns,
            dataframe_name="assignments",
        )

        self._check_columns(
            dataframe=self.time_entries,
            required_columns=time_entry_columns,
            dataframe_name="time_entries",
        )

        self._check_columns(
            dataframe=self.leave,
            required_columns=leave_columns,
            dataframe_name="leave",
        )

    @staticmethod
    def _check_columns(
        dataframe: pd.DataFrame,
        required_columns: set[str],
        dataframe_name: str,
    ) -> None:
        missing_columns = required_columns.difference(dataframe.columns)

        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))

            raise ValueError(
                f"{dataframe_name} is missing required columns: "
                f"{missing_text}"
            )

    def _normalise_assignments(self) -> None:
        date_columns = [
            "Assignment_Start",
            "Assignment_End",
        ]

        for column in date_columns:
            self.assignments[column] = pd.to_datetime(
                self.assignments[column],
                errors="coerce",
            )

        self.assignments["Is_Active_Assignment"] = (
            pd.to_numeric(
                self.assignments["Is_Active_Assignment"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        text_columns = [
            "Resource_Id",
            "ActivityAssignment_Id",
            "Consultant_Name",
            "Level",
            "Group",
            "Project_Name",
        ]

        for column in text_columns:
            self.assignments[column] = (
                self.assignments[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    def _normalise_time_entries(self) -> None:
        self.time_entries["WeekStart"] = pd.to_datetime(
            self.time_entries["WeekStart"],
            errors="coerce",
        )

        numeric_columns = [
            "Logged_Hours",
            "Consumed_Days",
            "Capacity",
        ]

        for column in numeric_columns:
            self.time_entries[column] = pd.to_numeric(
                self.time_entries[column],
                errors="coerce",
            ).fillna(0)

        self.time_entries["ActivityAssignment_Id"] = (
            self.time_entries["ActivityAssignment_Id"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    def _normalise_leave(self) -> None:
        self.leave["WeekStart"] = pd.to_datetime(
            self.leave["WeekStart"],
            errors="coerce",
        )

        self.leave["Leave_Hours"] = pd.to_numeric(
            self.leave["Leave_Hours"],
            errors="coerce",
        ).fillna(0)

        self.leave["Resource_Id"] = (
            self.leave["Resource_Id"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        self.leave["Leave_Info"] = (
            self.leave["Leave_Info"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    def summary(self) -> dict[str, int]:
        """
        Hızlı kontrol ve cache_info.json için özet bilgiler üretir.
        """

        return {
            "assignment_rows": len(self.assignments),
            "time_entry_rows": len(self.time_entries),
            "leave_rows": len(self.leave),
            "consultants": self.assignments[
                "Consultant_Name"
            ].nunique(),
            "projects": self.assignments.loc[
                self.assignments["Project_Name"] != "",
                "Project_Name",
            ].nunique(),
        }