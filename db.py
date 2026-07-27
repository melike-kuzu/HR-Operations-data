from __future__ import annotations

import os

import pandas as pd
import pyodbc
from dotenv import load_dotenv


load_dotenv()


def _required_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Required environment variable {name!r} is not configured. "
            "Add it to the local .env file or deployment environment."
        )

    return value.strip()


def get_connection() -> pyodbc.Connection:
    driver = os.getenv(
        "SQL_DRIVER",
        "ODBC Driver 18 for SQL Server",
    )
    server = _required_environment_variable("SQL_SERVER")
    database = _required_environment_variable("SQL_DATABASE")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=15;"
    )

    return pyodbc.connect(connection_string)


def run_query_to_df(query: str) -> pd.DataFrame:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query)

        # Dynamic SQL and multi-statement scripts may return several
        # intermediate results before the actual tabular result.
        while cursor.description is None:
            if not cursor.nextset():
                return pd.DataFrame()

        columns = [
            column[0]
            for column in cursor.description
        ]
        rows = cursor.fetchall()

    return pd.DataFrame.from_records(
        rows,
        columns=columns,
    )