# app/computation/schemas.py

from typing import List, Dict, Optional
from pydantic import BaseModel

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
    scenario_id: str
    year_count: int
    
    # Time Series Data (for charts)
    yearly_data: List[YearlyResult]
    
    # Aggregates (for summary cards)
    total_cost_npv: float
    final_network_condition: float