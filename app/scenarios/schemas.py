# app/scenarios/schemas.py

from uuid import UUID
from typing import Any, Dict, Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class ScenarioAssumptionsBase(BaseModel):
    """
    'parameters' is where we keep actual sliders/inputs, e.g.
    {
      "analysis_period_years": 20,
      "discount_rate": 0.08,
      "annual_budget_million": 250,
      "unit_cost_reseal_per_km": 0.8,
      "unit_cost_reconstruct_per_km": 3.5,
      "routine_maintenance_pct": 0.03
    }
    """
    name: str
    description: Optional[str] = None
    is_baseline: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ScenarioCreate(ScenarioAssumptionsBase):
    pass


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_baseline: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None


class ScenarioRead(ScenarioAssumptionsBase):
    id: UUID
    project_id: UUID
    user_id: str
    created_at: datetime
    updated_at: datetime


class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    is_baseline: bool
    created_at: datetime