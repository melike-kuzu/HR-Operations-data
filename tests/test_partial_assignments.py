import pandas as pd
import pytest

from tests.test_utilisation import load_master_data

from engine.reports.partial_assignments import (
    OUTPUT_COLUMNS,
    build_partial_assignments,
)


@pytest.fixture(scope="module")
def master_data():
    return load_master_data()


@pytest.fixture(scope="module")
def partial_assignments(master_data):
    return build_partial_assignments(
        data=master_data,
        run_date="2026-07-20",
    )


def test_partial_assignments_returns_dataframe(
    partial_assignments,
):
    assert isinstance(
        partial_assignments,
        pd.DataFrame,
    )


def test_partial_assignments_columns(
    partial_assignments,
):
    assert list(
        partial_assignments.columns
    ) == OUTPUT_COLUMNS


def test_partial_assignments_business_rules(
    partial_assignments,
):
    if partial_assignments.empty:
        pytest.skip(
            "No partial assignments were found "
            "for the selected test date."
        )

    weeks_column = (
        "Weeks assigned to project "
        "(<100% billable)"
    )

    assert (
        partial_assignments[weeks_column] > 0
    ).all()

    assert partial_assignments[
        weeks_column
    ].notna().all()

    assert (
        partial_assignments["Time (%)"] > 0
    ).all()

    assert (
        partial_assignments["Time (%)"] < 100
    ).all()


def test_partial_assignments_has_no_exact_duplicates(
    partial_assignments,
):
    if partial_assignments.empty:
        pytest.skip(
            "No partial assignments were found "
            "for the selected test date."
        )

    duplicate_mask = partial_assignments.duplicated(
        keep=False
    )

    assert not duplicate_mask.any(), (
        "The report contains exact duplicate rows:\n"
        f"{partial_assignments.loc[duplicate_mask]}"
    )


def test_partial_assignments_sorting(
    partial_assignments,
):
    if partial_assignments.empty:
        pytest.skip(
            "No partial assignments were found "
            "for the selected test date."
        )

    weeks_column = (
        "Weeks assigned to project "
        "(<100% billable)"
    )

    expected = (
        partial_assignments
        .sort_values(
            [
                weeks_column,
                "Resource name",
                "Client",
            ],
            ascending=[
                False,
                True,
                True,
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    actual = partial_assignments.reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(
        actual,
        expected,
    )


def test_partial_assignments_preview(
    partial_assignments,
):
    print(
        "\nPartial Assignments preview:"
    )

    print(
        partial_assignments.head(20).to_string(
            index=False
        )
    )