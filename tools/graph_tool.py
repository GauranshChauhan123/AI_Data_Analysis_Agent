
import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from langchain_core.tools import tool


# ---------- Helper functions ----------

def _save_or_show(output_path=None):
    try:
        plt.tight_layout()

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight")

        if matplotlib.get_backend().lower() not in ["agg", "template"]:
            plt.show()
    finally:
        plt.close()


def _plot(df, chart_type, x_col, y_col, hue_col, bins, title):
    plt.figure(figsize=(8, 5))

    if chart_type == "bar":
        if y_col and y_col in df.columns:
            sns.barplot(data=df, x=x_col, y=y_col, hue=x_col, palette="viridis", legend=False)
        else:
            sns.countplot(data=df, x=x_col, hue=x_col, palette="viridis", legend=False)
        plt.xticks(rotation=45)

    elif chart_type == "line":
        df = df.sort_values(x_col)
        sns.lineplot(data=df, x=x_col, y=y_col, marker="o")
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)

    elif chart_type == "scatter":
        sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col)

    elif chart_type == "histogram":
        sns.histplot(data=df, x=x_col, bins=bins, kde=True)

    elif chart_type == "pie":
        data = df.groupby(x_col)[y_col].sum()
        plt.pie(data, labels=data.index, autopct="%1.1f%%", startangle=140)
        plt.axis("equal")

    elif chart_type == "box":
        sns.boxplot(data=df, x=x_col, y=y_col, hue=x_col, palette="Set2", legend=False)

    elif chart_type == "heatmap":
        sns.heatmap(df.select_dtypes(include="number").corr(),
                    annot=True, cmap="coolwarm", fmt=".2f")

    plt.title(title or chart_type.replace("_", " ").title())

    if chart_type not in ["pie", "heatmap"]:
        plt.xlabel(x_col)
    if chart_type not in ["histogram", "pie", "heatmap"]:
        plt.ylabel(y_col if (y_col and y_col in df.columns) else "Count")


def _validate_columns(df, chart_type, x_col, y_col, hue_col):
    has_y_col = bool(y_col and y_col in df.columns)
    required = {
        "bar": [x_col, y_col] if has_y_col else [x_col],
        "line": [x_col, y_col],
        "scatter": [x_col, y_col],
        "histogram": [x_col],
        "pie": [x_col, y_col],
        "box": [x_col, y_col],
        "heatmap": []
    }

    for column in required[chart_type]:
        if not column:
            raise ValueError(f"{chart_type} requires the appropriate column names.")
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found. Available: {list(df.columns)}")

    if hue_col and hue_col not in df.columns:
        raise ValueError(f"Hue column '{hue_col}' not found.")

    numeric_columns = {
        "histogram": [x_col],
        "scatter": [x_col, y_col],
        "box": [y_col],
        "pie": [y_col],
        "bar": [y_col] if has_y_col else [],
        "line": [y_col]
    }

    for column in numeric_columns.get(chart_type, []):
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Column '{column}' must be numeric.")

    if chart_type == "heatmap":
        if len(df.select_dtypes(include="number").columns) < 2:
            raise ValueError("Heatmap requires at least two numeric columns.")


# ---------- Main tool ----------

@tool
def generate_graph(
    file_path: str,
    chart_type: str,
    x_col: str = "",
    y_col: str = "",
    hue_col: str = "",
    column: str = "",
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    bins: int = 15,
    output_path: str = ""
) -> dict:
    """Generate a bar, line, scatter, histogram, pie, box, or heatmap chart."""

    try:
        if not os.path.isfile(file_path):
            return {"success": False, "error": "Input file does not exist."}

        if not file_path.lower().endswith(".csv"):
            return {"success": False, "error": "Input must be a CSV file."}

        df = pd.read_csv(file_path)

        if df.empty:
            return {"success": False, "error": "Dataset is empty."}

        aliases = {
            "bar_chart": "bar",
            "line_graph": "line",
            "line_chart": "line",
            "scatter_plot": "scatter",
            "hist": "histogram",
            "pie_chart": "pie",
            "box_plot": "box",
            "boxplot": "box",
            "heat_map": "heatmap",
            "correlation_heatmap": "heatmap"
        }

        chart_type = chart_type.strip().lower().replace("-", "_").replace(" ", "_")
        chart_type = aliases.get(chart_type, chart_type)

        supported = ["bar", "line", "scatter", "histogram", "pie", "box", "heatmap"]

        if chart_type not in supported:
            return {"success": False, "error": f"Unsupported chart type. Choose from: {supported}"}

        x_col = (x_col or column).strip()
        y_col = y_col.strip()
        hue_col = hue_col.strip() or None

        _validate_columns(df, chart_type, x_col, y_col, hue_col)

        if chart_type == "histogram":
            bins = max(1, int(bins))

        _plot(df, chart_type, x_col, y_col, hue_col, bins, title)

        if xlabel:
            plt.xlabel(xlabel)
        if ylabel:
            plt.ylabel(ylabel)

        save_path = output_path.strip() or "chart.png"
        _save_or_show(save_path)

        result = {
            "success": True,
            "chart_type": chart_type,
            "message": "Chart generated successfully."
        }

        if save_path:
            result["output_path"] = save_path

        return result

    except (ValueError, TypeError, OSError, KeyError,
            pd.errors.ParserError, pd.errors.EmptyDataError,
            UnicodeDecodeError) as e:
        plt.close("all")
        return {"success": False, "error": str(e)}
