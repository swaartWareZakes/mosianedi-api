# app/db/schemas.py

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

# ============================================================
# PROJECT Schemas
# ============================================================

class ProjectMetadata(BaseModel):
    project_name: str
    description: Optional[str] = None
    start_year: int
    forecast_duration: int
    discount_rate: float


class ProjectDB(BaseModel):
    id: UUID
    user_id: UUID
    project_name: str
    description: Optional[str] = None
    start_year: int
    forecast_duration: int
    discount_rate: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================
# MASTER DATA Schemas
# ============================================================

class MasterDataUploadStatus(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    original_filename: str
    mime_type: str
    file_size: int
    status: str
    row_count: Optional[int] = None
    validation_errors: Optional[Dict[str, Any]] = None
    created_at: datetime