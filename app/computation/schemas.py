from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# INPUT: Simulation run options (from frontend)
# ============================================================

class SimulationRunOptions(BaseModel):
    """
    Options passed when triggering a run.
    Frontend may send either snake_case or camelCase aliases.
    """
    start_year_override: Optional[int] = Field(None, alias="startYearOverride")
    include_paved: bool = Field(True, alias="includePaved")
    include_gravel: bool = Field(True, alias="includeGravel")

    # New fields for history context
    run_name: Optional[str] = Field(None, alias="runName")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


# ============================================================
# OUTPUT: Core simulation payload (The Math Results)
# ============================================================

class YearlyResult(BaseModel):
    year: int
    avg_condition_index: float
    pct_good: float
    pct_fair: float
    pct_poor: float
    total_maintenance_cost: float
    asset_value: float


class SimulationOutput(BaseModel):
    project_id: str
    year_count: int
    yearly_data: List[YearlyResult]
    total_cost_npv: float
    final_network_condition: float
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# OUTPUT: DB row wrapper (History & Audit)
# ============================================================

class SimulationRunOut(BaseModel):
    id: UUID
    project_id: UUID
    scenario_id: Optional[UUID] = None
    run_at: datetime
    triggered_by: Optional[UUID] = None
    status: str = "completed"

    # The calculated results
    results_payload: SimulationOutput

    # The Context (Snapshots)
    run_name: Optional[str] = None
    run_options: Dict[str, Any] = {}
    assumptions_snapshot: Dict[str, Any] = {}
    network_snapshot: Dict[str, Any] = {}
    notes: Optional[str] = None

    class Config:
        from_attributes = True