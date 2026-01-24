from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ReportCreate(BaseModel):
    title: str
    report_type: str = Field(default="treasury_pack")  # executive, engineering, gis, treasury_pack
    simulation_run_id: UUID
    ai_insight_id: Optional[UUID] = None

    # toggles for what to include in the compiled report
    config: Dict[str, bool] = Field(
        default_factory=lambda: {
            "show_cost_of_doing_nothing": True,
            "show_asset_value": True,
            "include_engineering_details": False,
        }
    )


class ReportOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    report_type: str
    status: str = "draft"
    public_share_slug: Optional[str] = None
    created_at: datetime

    # compiled view payload (optional depending on endpoint)
    simulation_data: Optional[Dict[str, Any]] = None
    ai_narrative: Optional[Dict[str, Any]] = None
    project_meta: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True