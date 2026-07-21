import pytest

from tests.test_utilisation import load_master_data

from engine.reports.bench_status import (
    build_bench_status,
)


@pytest.fixture(scope="module")
def master_data():
    return load_master_data()


def test_bench_status(master_data):

    bench = build_bench_status(
        data=master_data,
        run_date="2026-07-20",
    )

    required_columns = [
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

    for column in required_columns:
        assert column in bench.columns, (
            f"Eksik kolon: {column}"
        )

    assert (
        bench["Possible Next Assignment"]
        .fillna("")
        .eq("")
        .all()
    )

    non_null_bench_weeks = (
        bench["Bench Weeks"]
        .dropna()
    )

    assert (
        non_null_bench_weeks >= 0
    ).all()

    print(bench.head(20))