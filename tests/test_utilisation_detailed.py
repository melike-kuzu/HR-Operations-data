import pytest

from tests.test_utilisation import load_master_data

from engine.reports.utilisation import (
    build_utilisation_detailed,
)


@pytest.fixture(scope="module")
def master_data():
    return load_master_data()


def test_utilisation_detailed(master_data):

    detailed = build_utilisation_detailed(
        data=master_data,
        run_date="2026-07-20",
    )

    assert not detailed.empty

    required_columns = [
        "Consultant_Name",
        "Level",
        "Group",
        "Location",
    ]

    for column in required_columns:
        assert column in detailed.columns, (
            f"Eksik kolon: {column}"
        )

    weekly_columns = [
        column
        for column in detailed.columns
        if column not in required_columns
    ]

    assert weekly_columns, (
        "Haftalık utilisation kolonları bulunamadı."
    )

    allowed_values = {
        "B",
        "L",
        "1.00",
    }

    actual_values = set(
        detailed[weekly_columns]
        .stack()
        .dropna()
        .astype(str)
        .unique()
    )

    invalid_values = {
        value
        for value in actual_values
        if (
            value not in allowed_values
            and not _is_capacity_value(value)
        )
    }

    assert not invalid_values, (
        "Beklenmeyen CalendarValue değerleri bulundu: "
        f"{sorted(invalid_values)}"
    )

    print(
        detailed[
            required_columns
            + weekly_columns[-3:]
        ].head(10)
    )


def _is_capacity_value(value: str) -> bool:
    """
    0.00 ile 1.00 arasındaki kapasite değerlerini kontrol eder.
    """

    try:
        numeric_value = float(value)
    except ValueError:
        return False

    return 0 <= numeric_value <= 1