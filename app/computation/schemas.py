from typing import List
from pydantic import BaseModel
from datetime import datetime

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
    
    # Time Series Data (for charts)
    yearly_data: List[YearlyResult]
    
    # Aggregates (for summary cards)
    total_cost_npv: float
    final_network_condition: float
    
    generated_at: datetime = datetime.now()