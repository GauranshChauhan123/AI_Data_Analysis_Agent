
import os
import pandas as pd
from langchain_core.tools import tool


# ---------- Helper functions ----------

def _drop_missing(df):
    return df.dropna()


def _remove_duplicates(df):
    return df.drop_duplicates()


def _fill_missing(df, column, value):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")

    val_str = str(value).strip().lower()

    if val_str == "mode":
        modes = df[column].dropna().mode()
        if modes.empty:
            raise ValueError(f"Column '{column}' has no mode.")
        fill_val = modes.iloc[0]

    elif val_str in ["mean", "median"]:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Cannot calculate {val_str} for non-numeric column '{column}'.")

        fill_val = df[column].mean() if val_str == "mean" else df[column].median()

    elif pd.api.types.is_numeric_dtype(df[column]):
        fill_val = pd.to_numeric(value, errors="raise")

    else:
        fill_val = value

    df[column] = df[column].fillna(fill_val)
    return df



def _rename_column(df, column, new_column_name):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
    if not new_column_name or new_column_name in df.columns:
        raise ValueError("New column name is empty or already exists.")

    return df.rename(columns={column: new_column_name})


def _drop_column(df, column):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")

    return df.drop(columns=[column])


def _filter_rows(df, column, operator, value):
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")

    series = df[column]

    if operator not in ["==", "!=", ">", "<", ">=", "<="]:
        raise ValueError("Unsupported filter operator.")

    if operator in [">", "<", ">=", "<="]:
        if not pd.api.types.is_numeric_dtype(series):
            raise ValueError("Numeric comparisons require a numeric column.")
        value = pd.to_numeric(value, errors="raise")
    elif pd.api.types.is_numeric_dtype(series):
        value = pd.to_numeric(value, errors="raise")

    conditions = {
        "==": lambda: series == value,
        "!=": lambda: series != value,
        ">": lambda: series > value,
        "<": lambda: series < value,
        ">=": lambda: series >= value,
        "<=": lambda: series <= value,
    }

    return df.loc[conditions[operator]()]


# ---------- Main tool ----------

@tool
def modify_dataset(
    file_path: str,
    operation: str,
    output_path: str,
    column: str = "",
    value: str = "",
    new_column_name: str = "",
    operator: str = ""
) -> dict:
    """Modify a CSV using supported operations and save to a separate file.

    Operations:
    drop_missing, remove_duplicates, fill_missing,
    rename_column, drop_column, filter_rows.
    """
    try:
        if not os.path.isfile(file_path):
            return {"success": False, "error": "Input file does not exist."}

        if not file_path.lower().endswith(".csv"):
            return {"success": False, "error": "Input must be a CSV file."}

        if not output_path.lower().endswith(".csv"):
            return {"success": False, "error": "Output must be a CSV file."}

        if os.path.abspath(file_path) == os.path.abspath(output_path):
            return {"success": False, "error": "Cannot overwrite the original file."}

        df = pd.read_csv(file_path)
        original_rows = len(df)

        if operation == "drop_missing":
            df = _drop_missing(df)

        elif operation == "remove_duplicates":
            df = _remove_duplicates(df)

        elif operation == "fill_missing":
            df = _fill_missing(df, column, value)

        elif operation == "rename_column":
            df = _rename_column(df, column, new_column_name)

        elif operation == "drop_column":
            df = _drop_column(df, column)

        elif operation == "filter_rows":
            df = _filter_rows(df, column, operator, value)

        else:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}"
            }

        df.to_csv(output_path, index=False)

        return {
            "success": True,
            "operation": operation,
            "original_rows": original_rows,
            "remaining_rows": len(df),
            "removed_rows": original_rows - len(df),
            "output_path": output_path
        }

    except (ValueError, TypeError, OSError,
            pd.errors.ParserError, pd.errors.EmptyDataError,
            UnicodeDecodeError) as e:
        return {"success": False, "error": str(e)}
