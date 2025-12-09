# app/master_data/schemas.py
from typing import Any, Dict, List
from pydantic import BaseModel


class DataPreviewResponse(BaseModel):
    preview_data: List[Dict[str, Any]]
    total_rows: int
    columns: List[str]