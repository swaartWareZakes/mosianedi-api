from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# --- NEW: Robust Options Schema ---
class SimulationRunOptions(BaseModel):
    # Frontend sends "startYearOverride", we map it to snake_case for Python
    start_year_override: Optional[int] = Field(None, alias="startYearOverride")
    include_paved: bool = Field(True, alias="includePaved")
    include_gravel: bool = Field(True, alias="includeGravel")

    class Config:
        # Allow populating by either name (safe for all versions)
        populate_by_name = True

# --- Existing Output Schemas ---
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
    generated_at: datetime = datetime.now()