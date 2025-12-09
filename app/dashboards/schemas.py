# app/dashboards/schemas.py
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    is_favorite: bool = False
    layout: Optional[Dict[str, Any]] = None
    overrides: Optional[Dict[str, Any]] = None


class DashboardCreate(DashboardBase):
    """Payload for creating a dashboard."""
    pass


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None
    layout: Optional[Dict[str, Any]] = None
    overrides: Optional[Dict[str, Any]] = None


class DashboardOut(DashboardBase):
    id: UUID
    project_id: UUID
    user_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True