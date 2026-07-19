import os
import pyodbc
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pyodbc.connect(
        f"DRIVER={{{os.getenv('SQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

def run_query_to_df(query: str) -> pd.DataFrame:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(query)

    # Dynamic SQL / multi statement scriptlerde gerçek result set'i bul
    while cursor.description is None:
        if not cursor.nextset():
            cursor.close()
            conn.close()
            return pd.DataFrame()

    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return pd.DataFrame.from_records(rows, columns=columns)