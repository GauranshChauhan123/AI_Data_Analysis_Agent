
import os
import pandas as pd
from langchain_core.tools import tool


def _dataset_overview(df):
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "duplicate_rows": int(df.duplicated().sum())
    }


def _missing_summary(df):
    missing = df.isnull().sum()
    return {
        column: int(count)
        for column, count in missing.items()
    }


def _numeric_summary(df):
    summary = df.describe()

    return summary.to_string()


def _build_report(df, file_path):
    overview = _dataset_overview(df)
    missing = _missing_summary(df)

    report = f"""
DATA ANALYSIS REPORT
====================

Source file: {file_path}

1. DATASET OVERVIEW
-------------------
Rows: {overview['rows']}
Columns: {overview['columns']}
Column names: {', '.join(map(str, overview['column_names']))}
Duplicate rows: {overview['duplicate_rows']}

2. MISSING VALUES
-----------------
"""

    for column, count in missing.items():
        report += f"{column}: {count}\n"

    report += f"""
3. NUMERIC STATISTICS
---------------------
{_numeric_summary(df)}

"""

    return report


@tool
def generate_report(file_path: str, output_path: str) -> dict:
    """Generate a text analysis report for a CSV dataset and save it to a file."""

    try:
        if not os.path.isfile(file_path):
            return {"success": False, "error": "Input file does not exist."}

        if not file_path.lower().endswith(".csv"):
            return {"success": False, "error": "Input must be a CSV file."}

        if not output_path.lower().endswith(".txt"):
            return {"success": False, "error": "Output must be a TXT file."}

        df = pd.read_csv(file_path)

        if df.empty:
            return {"success": False, "error": "Dataset is empty."}

        report = _build_report(df, file_path)

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(report)

        return {
            "success": True,
            "output_path": output_path,
            "rows_analyzed": len(df),
            "columns_analyzed": len(df.columns),
            "message": "Report generated successfully."
        }

    except (OSError, ValueError, pd.errors.ParserError,
            pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        return {"success": False, "error": str(e)}
