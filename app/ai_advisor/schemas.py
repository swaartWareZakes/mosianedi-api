from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class AiInsightBase(BaseModel):
    insight_type: str = "treasury_narrative"
    status: str = "draft"
    content: Dict[str, Any]


class AiInsightOut(AiInsightBase):
    id: UUID
    project_id: UUID
    simulation_run_id: Optional[UUID] = None
    created_at: datetime
    created_by: Optional[UUID] = None

    # Small snippet so frontend can label “based on Run X…”
    simulation_summary: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True