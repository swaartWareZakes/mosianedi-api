# app/scenarios/schemas.py

from uuid import UUID
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

# --- The shape of the JSON stored in 'parameters' column ---
# This matches the sliders on your frontend
class RonetParameters(BaseModel):
    analysis_duration: int = Field(20, ge=5, le=30, description="Analysis period in years")
    budget_strategy: Literal["unconstrained", "fixed_limit", "percent_baseline"] = "percent_baseline"
    annual_budget_cap: Optional[float] = None
    budget_percent_baseline: int = Field(100, ge=50, le=150, description="% of required budget")
    policy_bias: Literal["preventive", "balanced", "reactive"] = "balanced"
    discount_rate: float = 8.0

# --- CRUD Schemas ---

class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_baseline: bool = False
    # Default to standard parameters if none provided
    parameters: RonetParameters = Field(default_factory=RonetParameters)

class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    # Allow partial updates to parameters
    parameters: Optional[RonetParameters] = None

class ScenarioRead(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    is_baseline: bool
    parameters: RonetParameters  # API always returns parsed structure
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    is_baseline: bool
    created_at: datetime