from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from workforce_assistant.ingestion.chunking import chunk_text
from workforce_assistant.ingestion.models import IngestionDocument


PROFILE_SOURCE_TYPE = "profile_generator"
NO_KNOWLEDGE_VALUES = {
    "",
    "nan",
    "none",
    "no knowledge",
}


def build_profile_generator_documents(
    file_path: str | Path,
) -> list[IngestionDocument]:
    """
    Read Profile Generator Excel and produce Azure Search documents.

    Only current employees from the Employee list are indexed.
    Pivot/display sheets such as Profile and Skills Matrix are ignored;
    their normalised DB equivalents are used instead.
    """
    source_path = Path(file_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Profile Generator file was not found: {source_path}"
        )

    sheets = pd.read_excel(
        source_path,
        sheet_name=[
            "Employee list",
            "Short Profile DB",
            "Technologies DB",
            "Technical Expertise DB",
            "Business Expertise DB",
            "Professional experience DB",
            "Academic qualifications DB",
            "Trainings DB",
            "Certifications DB",
            "Languages DB",
        ],
    )

    employees = _prepare_employee_list(
        sheets["Employee list"]
    )

    allowed_names = set(
        employees["Employee Name"].dropna().astype(str)
    )

    documents: list[IngestionDocument] = []

    for _, employee in employees.iterrows():
        employee_name = _clean_text(
            employee.get("Employee Name")
        )

        if not employee_name:
            continue

        employee_key = _normalise_name(employee_name)

        base_metadata = {
            "record_type": "consultant_profile",
            "consultant_id": _clean_text(
                employee.get("Email")
            ),
            "level": _clean_text(
                employee.get("Job level")
            ),
            "group": _clean_text(
                employee.get("Group")
            ),
            "office": _clean_text(
                employee.get("Office")
            ),
            "is_active": True,
        }

        overview = _build_overview(employee)

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Overview",
                section_content=overview,
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": [],
                },
            )
        )

        short_profile_rows = _rows_for_employee(
            sheets["Short Profile DB"],
            employee_column="Consultant Name",
            employee_name=employee_name,
        )

        short_profile = _build_short_profile(
            short_profile_rows
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Short profile",
                section_content=short_profile,
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": [],
                },
            )
        )

        technology_rows = _filter_current_knowledge_rows(
            _rows_for_employee(
                sheets["Technologies DB"],
                employee_column="EmployeeName",
                employee_name=employee_name,
            )
        )

        technologies, technology_skills = (
            _build_technologies(technology_rows)
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Technologies",
                section_content=technologies,
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": technology_skills,
                },
            )
        )

        technical_rows = _filter_current_knowledge_rows(
            _rows_for_employee(
                sheets["Technical Expertise DB"],
                employee_column="EmployeeName",
                employee_name=employee_name,
            )
        )

        technical_expertise, technical_skills = (
            _build_named_knowledge_section(
                technical_rows,
                name_column="TechnicalExpertiseName",
            )
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Technical expertise",
                section_content=technical_expertise,
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": technical_skills,
                },
            )
        )

        business_rows = _filter_current_knowledge_rows(
            _rows_for_employee(
                sheets["Business Expertise DB"],
                employee_column="EmployeeName",
                employee_name=employee_name,
            )
        )

        business_expertise, business_skills = (
            _build_named_knowledge_section(
                business_rows,
                name_column="BusinessSkill",
                category_column="Category",
            )
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Business expertise",
                section_content=business_expertise,
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": business_skills,
                },
            )
        )

        experience_rows = _filter_current_rows(
            _rows_for_employee(
                sheets["Professional experience DB"],
                employee_column="EmployeeName",
                employee_name=employee_name,
            )
        )

        experience = _build_experience(
            experience_rows
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Professional experience",
                section_content=experience,
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": _collect_experience_technologies(
                        experience_rows
                    ),
                },
            )
        )

        academic_rows = _filter_current_rows(
            _rows_for_employee(
                sheets["Academic qualifications DB"],
                employee_column="EmployeeName",
                employee_name=employee_name,
            )
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Academic qualifications",
                section_content=_build_simple_rows(
                    academic_rows,
                    value_columns=[
                        "Academic qualification",
                    ],
                ),
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": [],
                },
            )
        )

        training_rows = _filter_current_rows(
            _rows_for_employee(
                sheets["Trainings DB"],
                employee_column="Employee name",
                employee_name=employee_name,
            )
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Trainings",
                section_content=_build_simple_rows(
                    training_rows,
                    value_columns=[
                        "Training",
                        "Vendor",
                        "Year",
                    ],
                ),
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": [],
                },
            )
        )

        certification_rows = _filter_current_rows(
            _rows_for_employee(
                sheets["Certifications DB"],
                employee_column="Employee name",
                employee_name=employee_name,
            )
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Certifications",
                section_content=_build_simple_rows(
                    certification_rows,
                    value_columns=[
                        "Certification",
                        "Vendor",
                        "Year",
                    ],
                ),
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": [],
                },
            )
        )

        language_rows = _filter_current_rows(
            _rows_for_employee(
                sheets["Languages DB"],
                employee_column="Employee name",
                employee_name=employee_name,
            )
        )

        documents.extend(
            _create_section_documents(
                consultant_name=employee_name,
                section_name="Languages",
                section_content=_build_simple_rows(
                    language_rows,
                    value_columns=[
                        "Language",
                        "Level",
                    ],
                ),
                source_file=source_path.name,
                metadata={
                    **base_metadata,
                    "skills": [],
                },
            )
        )

    # Defensive check: only current employees should survive.
    return [
        document
        for document in documents
        if document.consultant_name in allowed_names
    ]


def _prepare_employee_list(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    employees = dataframe.copy()

    employees["Employee Name"] = (
        employees["Employee Name"]
        .astype("string")
        .str.strip()
    )

    status = (
        employees["Employment status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    employees = employees[
        status.eq("current")
        & employees["Employee Name"].notna()
    ]

    return employees.drop_duplicates(
        subset=["Employee Name"],
        keep="last",
    )


def _rows_for_employee(
    dataframe: pd.DataFrame,
    *,
    employee_column: str,
    employee_name: str,
) -> pd.DataFrame:
    if employee_column not in dataframe.columns:
        return dataframe.iloc[0:0].copy()

    names = (
        dataframe[employee_column]
        .astype("string")
        .str.strip()
        .str.casefold()
    )

    return dataframe[
        names.eq(employee_name.strip().casefold())
    ].copy()


def _filter_current_rows(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if dataframe.empty or "Status" not in dataframe.columns:
        return dataframe

    status = (
        dataframe["Status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    return dataframe[
        status.eq("current") | status.isna()
    ].copy()


def _filter_current_knowledge_rows(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = _filter_current_rows(dataframe)

    if result.empty or "Level.1" not in result.columns:
        return result

    knowledge = (
        result["Level.1"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    return result[
        ~knowledge.isin(NO_KNOWLEDGE_VALUES)
        & knowledge.notna()
    ].copy()


def _build_overview(
    employee: pd.Series,
) -> str:
    fields = [
        ("Employee name", employee.get("Employee Name")),
        ("Job title", employee.get("Job Title")),
        ("Job level", employee.get("Job level")),
        ("Group", employee.get("Group")),
        ("Function", employee.get("Function")),
        ("Office", employee.get("Office")),
        ("Working model", employee.get("Working model")),
        ("Working location", employee.get("Working location")),
        (
            "Years at ClearPeaks",
            _format_number(
                employee.get("Years at ClearPeaks")
            ),
        ),
        (
            "Employment start date",
            _format_date(
                employee.get("Employment start date")
            ),
        ),
    ]

    return "\n".join(
        f"{label}: {cleaned}"
        for label, value in fields
        if (cleaned := _clean_text(value))
    )


def _build_short_profile(
    dataframe: pd.DataFrame,
) -> str:
    if dataframe.empty:
        return ""

    rows = []

    for _, row in dataframe.iterrows():
        parts = [
            _label_value("Summary", row.get("Summary")),
            _label_value("Customer", row.get("Customer")),
            _label_value("Project", row.get("Project")),
        ]

        text = "\n".join(
            part for part in parts if part
        )

        if text:
            rows.append(text)

    return "\n\n".join(rows)


def _build_technologies(
    dataframe: pd.DataFrame,
) -> tuple[str, list[str]]:
    if dataframe.empty:
        return "", []

    lines: list[str] = []
    skills: list[str] = []

    for _, row in dataframe.iterrows():
        technology = _clean_text(
            row.get("TechnologyName")
        )

        if not technology:
            continue

        level = _clean_text(
            row.get("Level.1")
        )
        vendor = _clean_text(
            row.get("Vendor")
        )
        technology_type = _clean_text(
            row.get("Type")
        )

        details = [
            value
            for value in [
                level,
                f"Vendor: {vendor}" if vendor else "",
                (
                    f"Category: {technology_type}"
                    if technology_type
                    else ""
                ),
            ]
            if value
        ]

        line = technology

        if details:
            line += " — " + "; ".join(details)

        lines.append(line)
        skills.append(technology)

    return (
        "\n".join(_deduplicate(lines)),
        _deduplicate(skills),
    )


def _build_named_knowledge_section(
    dataframe: pd.DataFrame,
    *,
    name_column: str,
    category_column: str | None = None,
) -> tuple[str, list[str]]:
    if dataframe.empty:
        return "", []

    lines: list[str] = []
    skills: list[str] = []

    for _, row in dataframe.iterrows():
        name = _clean_text(
            row.get(name_column)
        )

        if not name:
            continue

        level = _clean_text(
            row.get("Level.1")
        )

        category = (
            _clean_text(row.get(category_column))
            if category_column
            else ""
        )

        details = [
            value
            for value in [
                level,
                f"Category: {category}"
                if category
                else "",
            ]
            if value
        ]

        line = name

        if details:
            line += " — " + "; ".join(details)

        lines.append(line)
        skills.append(name)

    return (
        "\n".join(_deduplicate(lines)),
        _deduplicate(skills),
    )


def _build_experience(
    dataframe: pd.DataFrame,
) -> str:
    if dataframe.empty:
        return ""

    rows: list[str] = []

    for _, row in dataframe.iterrows():
        fields = [
            ("Company", row.get("CompanyName")),
            ("Customer", row.get("CustomerName")),
            ("Industry", row.get("Industry")),
            ("Period", row.get("Period")),
            (
                "Duration in months",
                row.get(
                    "Duration of the project (in months)"
                ),
            ),
            (
                "Project title",
                row.get("Title of the Project"),
            ),
            ("Description", row.get("Project")),
            (
                "Technologies",
                row.get("CONCAT Technologies"),
            ),
        ]

        text = "\n".join(
            f"{label}: {cleaned}"
            for label, value in fields
            if (cleaned := _clean_text(value))
        )

        if text:
            rows.append(text)

    return "\n\n".join(rows)


def _collect_experience_technologies(
    dataframe: pd.DataFrame,
) -> list[str]:
    values: list[str] = []

    for column in [
        "Technology1",
        "Technology2",
        "Technology3",
        "Technology4",
        "Technology5",
        "Technology6",
    ]:
        if column not in dataframe.columns:
            continue

        values.extend(
            _clean_text(value)
            for value in dataframe[column].tolist()
            if _clean_text(value)
        )

    return _deduplicate(values)


def _build_simple_rows(
    dataframe: pd.DataFrame,
    *,
    value_columns: list[str],
) -> str:
    if dataframe.empty:
        return ""

    lines: list[str] = []

    for _, row in dataframe.iterrows():
        values = [
            _clean_text(row.get(column))
            for column in value_columns
        ]

        values = [
            value for value in values if value
        ]

        if values:
            lines.append(" — ".join(values))

    return "\n".join(_deduplicate(lines))


def _create_section_documents(
    *,
    consultant_name: str,
    section_name: str,
    section_content: str,
    source_file: str,
    metadata: dict[str, Any],
) -> list[IngestionDocument]:
    clean_content = section_content.strip()

    if not clean_content:
        return []

    full_content = (
        f"Consultant: {consultant_name}\n"
        f"Section: {section_name}\n\n"
        f"{clean_content}"
    )

    chunks = chunk_text(
        full_content,
        chunk_size=5000,
        overlap=300,
    )

    documents: list[IngestionDocument] = []

    for chunk_number, chunk in enumerate(
        chunks,
        start=1,
    ):
        document_id = _build_document_id(
            consultant_name=consultant_name,
            section_name=section_name,
            chunk_number=chunk_number,
        )

        documents.append(
            IngestionDocument(
                id=document_id,
                content=chunk,
                title=(
                    f"{consultant_name} — "
                    f"{section_name}"
                ),
                source_type=PROFILE_SOURCE_TYPE,
                source_file=source_file,
                consultant_name=consultant_name,
                metadata={
                    **metadata,
                    "sheet_name": section_name,
                    "chunk_id": document_id,
                    "row_number": chunk_number,
                },
            )
        )

    return documents


def _build_document_id(
    *,
    consultant_name: str,
    section_name: str,
    chunk_number: int,
) -> str:
    raw_value = (
        f"{consultant_name}|"
        f"{section_name}|"
        f"{chunk_number}"
    )

    return hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()


def _label_value(
    label: str,
    value: Any,
) -> str:
    clean_value = _clean_text(value)

    if not clean_value:
        return ""

    return f"{label}: {clean_value}"


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in {"nan", "none", "nat"}:
        return ""

    return " ".join(text.split())


def _format_number(
    value: Any,
) -> str:
    try:
        if pd.isna(value):
            return ""

        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return _clean_text(value)


def _format_date(
    value: Any,
) -> str:
    if value is None:
        return ""

    try:
        timestamp = pd.Timestamp(value)

        if pd.isna(timestamp):
            return ""

        return timestamp.date().isoformat()
    except (TypeError, ValueError):
        return _clean_text(value)


def _normalise_name(
    value: str,
) -> str:
    return " ".join(
        value.strip().casefold().split()
    )


def _deduplicate(
    values: Iterable[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        clean_value = _clean_text(value)

        if not clean_value:
            continue

        key = clean_value.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(clean_value)

    return result