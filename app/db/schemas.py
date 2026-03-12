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
    scope: str = 'provincial' # provincial, municipal, local, route
    municipality: Optional[str] = None
    local_area: Optional[str] = None
    
    # --- NEW FIELDS FOR ROUTE SCOPE ---
    route_name: Optional[str] = None
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    route_length_km: Optional[float] = 0.0
    surface_type: Optional[str] = 'paved'
    climate_zone: Optional[str] = 'dry_sub_humid'
    route_specific_vci: Optional[int] = None
    route_daily_traffic: Optional[int] = None


class ProjectDB(BaseModel):
    id: UUID
    user_id: UUID
    project_name: str
    province: str
    start_year: int
    scope: Optional[str] = 'provincial'
    municipality: Optional[str] = None
    local_area: Optional[str] = None
    
    # --- ROUTE DATA ---
    route_name: Optional[str] = None
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    route_length_km: Optional[float] = 0.0
    surface_type: Optional[str] = 'paved'
    climate_zone: Optional[str] = 'dry_sub_humid'
    route_specific_vci: Optional[int] = None
    route_daily_traffic: Optional[int] = None
    
    # Status fields from DB
    status: Optional[str] = None
    proposal_title: Optional[str] = None
    proposal_status: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: UUID
    user_id: UUID
    project_name: str
    province: str
    start_year: int
    scope: Optional[str] = 'provincial'
    municipality: Optional[str] = None
    local_area: Optional[str] = None
    
    # --- ROUTE DATA ---
    route_name: Optional[str] = None
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    route_length_km: Optional[float] = 0.0
    surface_type: Optional[str] = 'paved'
    climate_zone: Optional[str] = 'dry_sub_humid'
    route_specific_vci: Optional[int] = None
    route_daily_traffic: Optional[int] = None
    
    status: str
    locked: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    active_simulation_run_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None

    class Config:
        from_attributes = True