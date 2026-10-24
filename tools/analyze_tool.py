
import pandas as pd
from langchain_core.tools import tool

@tool
def analyze_data(file_path: str, column: str) -> dict:
    """Calculate descriptive statistics for a numeric column."""

    df = pd.read_csv(file_path)

    if column not in df.columns:
        return {"error": f"Column '{column}' not found."}

    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"error": f"Column '{column}' is not numeric."}

    series = df[column].dropna()

    if series.empty:
        return {"error": f"Column '{column}' has no valid numeric values."}

    return {
        "column": column,
        "count": int(series.count()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "min": float(series.min()),
        "max": float(series.max()),
        "sum": float(series.sum()),
    }
