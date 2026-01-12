from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# ============================================================
# PROJECT Schemas (NEW - proposal-first flow)
# ============================================================

class ProjectMetadata(BaseModel):
    project_name: str
    province: str
    start_year: int


class ProjectDB(BaseModel):
    id: UUID
    user_id: UUID
    project_name: str
    province: str
    start_year: int

    # Optional fields if your DB has them (you SELECT them already)
    proposal_title: Optional[str] = None
    proposal_status: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True