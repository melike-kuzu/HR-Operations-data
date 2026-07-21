from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from engine.master_dataset import MasterData
from engine.business_logic import get_eligible_assignments


def build_bench_status(
    data: MasterData,
    run_date: str | date | datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Seçilen tarihte aktif projesi olmayan eligible consultantları döndürür.

    Consultant population:
        Consultant Tracker, Utilisation ve diğer raporlarla aynı
        eligible consultant population kullanılır.

    Bench Weeks:
        Consultant'ın seçilen tarihten önce tamamlanmış en son
        assignment bitiş tarihinden itibaren geçen tam hafta sayısıdır.

    Possible Next Assignment:
        Streamlit tarafında manuel giriş için boş bırakılır.
    """

    selected_date = (
        pd.Timestamp.today().normalize()
        if run_date is None
        else pd.Timestamp(run_date).normalize()
    )

    # Bütün raporlarda aynı consultant population kullanılır.
    assignments = get_eligible_assignments(
        assignments=data.assignments,
        as_of_date=selected_date,
    ).copy()

    required_columns = {
        "Resource_Id",
        "Consultant_Name",
        "Level",
        "Job_Title",
        "Group",
        "Location",
        "Project_Name",
        "Assignment_Start",
        "Assignment_End",
    }

    missing_columns = required_columns.difference(
        assignments.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Assignments data is missing columns: "
            f"{missing_text}"
        )

    assignments["Assignment_Start"] = pd.to_datetime(
        assignments["Assignment_Start"],
        errors="coerce",
    ).dt.normalize()

    assignments["Assignment_End"] = pd.to_datetime(
        assignments["Assignment_End"],
        errors="coerce",
    ).dt.normalize()

    consultant_columns = [
        "Resource_Id",
        "Consultant_Name",
        "Level",
        "Job_Title",
        "Group",
        "Location",
    ]

    # Eligible consultant population içinden her consultant için
    # tek satırlık temel bilgi oluştur.
    consultants = (
        assignments[
            consultant_columns
            + [
                "Assignment_Start",
                "Assignment_End",
            ]
        ]
        .sort_values(
            [
                "Resource_Id",
                "Assignment_End",
                "Assignment_Start",
            ],
            na_position="last",
        )
        .drop_duplicates(
            subset=["Resource_Id"],
            keep="last",
        )
        [consultant_columns]
        .copy()
    )

    # Seçilen tarihte aktif assignment bulunan consultantlar.
    active_mask = (
        assignments["Assignment_Start"].notna()
        & assignments["Assignment_Start"].le(
            selected_date
        )
        & (
            assignments["Assignment_End"].isna()
            | assignments["Assignment_End"].ge(
                selected_date
            )
        )
    )

    active_resource_ids = set(
        assignments.loc[
            active_mask,
            "Resource_Id",
        ]
        .dropna()
        .unique()
    )

    # Eligible population içinden aktif assignment'ı olmayanlar bench.
    bench = consultants.loc[
        ~consultants["Resource_Id"].isin(
            active_resource_ids
        )
    ].copy()

    # Seçilen tarihten önce bitmiş assignmentlar.
    completed_assignments = assignments.loc[
        assignments["Assignment_End"].notna()
        & assignments["Assignment_End"].lt(
            selected_date
        )
    ].copy()

    # Her consultant için en son biten assignment.
    latest_completed = (
        completed_assignments
        .sort_values(
            [
                "Resource_Id",
                "Assignment_End",
                "Assignment_Start",
            ],
            na_position="last",
        )
        .groupby(
            "Resource_Id",
            as_index=False,
            dropna=False,
        )
        .tail(1)
        [
            [
                "Resource_Id",
                "Project_Name",
                "Assignment_End",
            ]
        ]
        .rename(
            columns={
                "Project_Name": "Last Project",
                "Assignment_End": "Last Assignment End",
            }
        )
    )

    bench = bench.merge(
        latest_completed,
        on="Resource_Id",
        how="left",
        validate="one_to_one",
    )

    bench["Bench Weeks"] = (
        (
            selected_date
            - bench["Last Assignment End"]
        ).dt.days
        // 7
    )

    bench["Bench Weeks"] = (
        bench["Bench Weeks"]
        .where(
            bench["Last Assignment End"].notna()
        )
        .astype("Int64")
    )

    # Tarihi yalnızca YYYY-MM-DD formatında göster.
    last_assignment_end = pd.to_datetime(
        bench["Last Assignment End"],
        errors="coerce",
    )

    bench["Last Assignment End"] = (
        last_assignment_end.dt.strftime(
            "%Y-%m-%d"
        )
    )

    bench.loc[
        last_assignment_end.isna(),
        "Last Assignment End",
    ] = None

    bench["Possible Next Assignment"] = ""

    output_columns = [
        "Consultant_Name",
        "Level",
        "Job_Title",
        "Group",
        "Location",
        "Last Project",
        "Last Assignment End",
        "Bench Weeks",
        "Possible Next Assignment",
    ]

    bench = (
        bench[output_columns]
        .sort_values(
            [
                "Bench Weeks",
                "Consultant_Name",
            ],
            ascending=[
                False,
                True,
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    return bench