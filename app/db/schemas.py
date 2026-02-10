from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


# ============================================================
# PROJECT Schemas (proposal-first flow)
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
    
    # Status fields from DB
    status: Optional[str] = None
    proposal_title: Optional[str] = None
    proposal_status: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- NEW SCHEMA ---
class ProjectOut(BaseModel):
    id: UUID
    user_id: UUID
    project_name: str
    province: str
    start_year: int
    status: str
    locked: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    active_simulation_run_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None

    class Config:
        from_attributes = True