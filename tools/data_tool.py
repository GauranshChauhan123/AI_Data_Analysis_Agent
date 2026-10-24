import pandas as pd
from langchain_core.tools import tool
import os
import pandas as pd


@tool
def inspect_data(file_path: str) -> dict:
    """Inspect a CSV dataset and return its structure."""
    try:
        df = pd.read_csv(file_path, skipinitialspace=True)

        df.columns = df.columns.str.strip()

        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].str.strip()

        # Convert columns to numeric where values support it
        for col in df.columns:
            converted = pd.to_numeric(df[col], errors="coerce")

            # Convert only if all non-empty values are numeric
            non_empty = df[col].notna()
            if non_empty.any() and converted[non_empty].notna().all():
                df[col] = converted

        return {
            "success": True,
            "file_path": file_path,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "column_info": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "head": df.head().to_dict(orient="records"),
            "numeric_summary": df.describe().to_dict()
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@tool
def validate_dataset(file_path: str) -> dict:
    """Validate a CSV file before analysis."""

    if not os.path.exists(file_path):
        return {"valid": False, "error": "File does not exist."}

    if not os.path.isfile(file_path):
        return {"valid": False, "error": "Path is not a file."}

    if not file_path.lower().endswith(".csv"):
        return {"valid": False, "error": "Only CSV files are supported."}

    try:
        df = pd.read_csv(file_path)
    except (pd.errors.ParserError, UnicodeDecodeError, pd.errors.EmptyDataError):
        return {"valid": False, "error": "File is empty or is not a readable CSV."}
    except OSError:
        return {"valid": False, "error": "Unable to read the file."}

    if df.empty:
        return {"valid": False, "error": "Dataset has no rows."}

    if len(df.columns) == 0:
        return {"valid": False, "error": "Dataset has no columns."}

    if df.columns.duplicated().any():
        return {"valid": False, "error": "Dataset contains duplicate column names."}

    if any(str(col).strip() == "" for col in df.columns):
        return {"valid": False, "error": "Dataset contains empty column names."}

    return {
        "valid": True,
        "rows": len(df),
        "columns": len(df.columns),
        "message": "Dataset is valid and ready for analysis."
    }

