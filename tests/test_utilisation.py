from pathlib import Path

from db import run_query_to_df
from engine.master_dataset import MasterData
from engine.reports.utilisation import build_utilisation


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_sql(relative_path: str) -> str:
    """
    Proje köküne göre SQL dosyasını okur.
    """

    sql_path = PROJECT_ROOT / relative_path

    return sql_path.read_text(encoding="utf-8")


def load_master_data() -> MasterData:
    """
    Üç base SQL sorgusunu çalıştırıp MasterData oluşturur.
    """

    assignments = run_query_to_df(
        read_sql("sql/base/assignments.sql")
    )

    time_entries = run_query_to_df(
        read_sql("sql/base/weekly_time_entries.sql")
    )

    leave = run_query_to_df(
        read_sql("sql/base/weekly_leave.sql")
    )

    return MasterData(
        assignments=assignments,
        time_entries=time_entries,
        leave=leave,
    )


def test_utilisation():
    """
    Utilisation raporunun doğru yapıda üretildiğini kontrol eder.
    """

    data = load_master_data()

    utilisation = build_utilisation(
        data,
        run_date="2026-07-20",
    )

    assert not utilisation.empty, (
        "Utilisation raporu boş üretildi."
    )

    assert "Utilisation" in utilisation.columns, (
        "Utilisation ana kolonu bulunamadı. "
        f"Mevcut kolonlar: {utilisation.columns.tolist()}"
    )

    expected_metrics = [
        "Booked",
        "Unconfirmed",
        "Partly Booked",
        "On Leave",
        "Bench",
        "Booked Capacity",
        "Maximum Capacity",
        "Forecasted Allocation",
    ]

    actual_metrics = utilisation[
        "Utilisation"
    ].tolist()

    assert actual_metrics == expected_metrics, (
        "Utilisation satırları beklenen sırada değil.\n"
        f"Beklenen: {expected_metrics}\n"
        f"Gerçek: {actual_metrics}"
    )

    weekly_columns = [
        column
        for column in utilisation.columns
        if column != "Utilisation"
    ]

    assert weekly_columns, (
        "Utilisation raporunda haftalık kolon bulunamadı."
    )

    assert weekly_columns == sorted(weekly_columns), (
        "Haftalık kolonlar tarih sırasına göre sıralı değil."
    )

    print("\nUtilisation shape:")
    print(utilisation.shape)

    print("\nUtilisation preview:")
    print(utilisation.iloc[:, :8])

    print("\nUtilisation metrics:")
    print(utilisation["Utilisation"].tolist())

    print("\nFirst weekly columns:")
    print(weekly_columns[:10])