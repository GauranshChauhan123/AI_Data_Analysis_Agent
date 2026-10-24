
from pathlib import Path
import shutil
import uuid
from agent.graph import build_graph

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI(title="Data Analyst Agent API")

UPLOAD_DIR = Path("data/uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

graph=build_graph()

class AnalyzeRequest(BaseModel):
    file_id: str
    user_request: str


@app.get("/")
def read_root():
    return {"message": "Welcome to the Data Analyst Agent API"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")

    file_id = f"{uuid.uuid4().hex}.csv"
    path = UPLOAD_DIR / file_id

    with path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = pd.read_csv(path, skipinitialspace=True)
        df.columns = df.columns.str.strip()

        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].str.strip()

        for col in df.columns:
            converted = pd.to_numeric(df[col], errors="coerce")
            non_empty = df[col].notna()
            if non_empty.any() and converted[non_empty].notna().all():
                df[col] = converted

        df.to_csv(path, index=False)

        return {
            "file_id": file_id,
            "rows": len(df),
            "columns": len(df.columns),
            "column_types": df.dtypes.astype(str).to_dict(),
            "preview": df.head(10).fillna("").to_dict(orient="records"),
        }
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read CSV: {exc}")



@app.get("/summary/{file_id}")
def dataset_summary(file_id: str):
    if (
        Path(file_id).name != file_id
        or not file_id.lower().endswith(".csv")
    ):
        raise HTTPException(400, "Invalid CSV file ID.")

    file_path = (UPLOAD_DIR / file_id).resolve()

    if not file_path.is_relative_to(UPLOAD_DIR):
        raise HTTPException(400, "Invalid file path.")

    if not file_path.is_file():
        raise HTTPException(
            404,
            f"Dataset not found: {file_id}",
        )

    try:
        df = pd.read_csv(file_path)

        return {
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "total_missing_values": int(df.isna().sum().sum()),
            "columns": [
                {
                    "name": str(col),
                    "type": str(df[col].dtype),
                    "missing_values": int(df[col].isna().sum()),
                }
                for col in df.columns
            ],
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not summarize CSV: {exc}",
        )


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    # Prevent directory traversal and accept only CSV filenames
    if (
        Path(request.file_id).name != request.file_id
        or not request.file_id.lower().endswith(".csv")
    ):
        raise HTTPException(400, "Invalid CSV file ID.")

    file_path = (UPLOAD_DIR / request.file_id).resolve()

    if not file_path.is_relative_to(UPLOAD_DIR):
        raise HTTPException(400, "Invalid file path.")

    if not file_path.is_file():
        raise HTTPException(404, "Dataset not found.")

    initial_state = {
        "messages": [],
        "file_path": str(file_path),
        "user_request": request.user_request,
        "plan": [],
        "current_step": 0,
        "dataset_info": {},
        "results": [],
        "output_path": "",
        "errors": [],
        "summary": {},
    }

    try:
        result = graph.invoke(initial_state)

        return {
            "summary": result.get("summary", {}),
            "output_path": result.get("output_path", ""),
            "errors": result.get("errors", []),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        )
