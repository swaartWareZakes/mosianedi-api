import pandas as pd
import numpy as np
from uuid import UUID
from datetime import datetime

# UPDATED IMPORT: Using the new Forecast Schema
from app.scenarios.schemas import ForecastParametersOut
from .schemas import SimulationOutput, YearlyResult

def run_ronet_simulation(
    project_id: UUID,
    params: ForecastParametersOut,
    # For now, we simulate strictly based on the aggregate inputs
    # later we can re-add granular segment logic if needed
    current_condition: float = 50.0 
) -> SimulationOutput:
    
    yearly_results = []
    
    # Extract Parameters from the new Schema
    duration = params.analysis_duration
    inflation = params.cpi_percentage / 100.0
    deterioration_rate = 0.05 # Default 5% degradation if no money spent
    
    # Adjust deterioration based on user input
    if params.paved_deterioration_rate == "Fast":
        deterioration_rate = 0.08
    elif params.paved_deterioration_rate == "Slow":
        deterioration_rate = 0.02
        
    current_vci = current_condition
    # Dummy Budget Logic (replace with real calculation later)
    annual_budget = params.previous_allocation * (1 + inflation) 

    # --- SIMULATION LOOP ---
    for year in range(1, duration + 1):
        
        # 1. Apply Deterioration
        current_vci -= (current_vci * deterioration_rate)
        
        # 2. Apply Budget Effect (Money improves condition)
        # Simple heuristic: R100m improves VCI by 1 point (dummy logic)
        improvement = (annual_budget / 100_000_000) * 0.5
        current_vci += improvement
        
        # Cap VCI at 100
        if current_vci > 100: current_vci = 100
        if current_vci < 0: current_vci = 0

        yearly_results.append(YearlyResult(
            year=year,
            avg_condition_index=round(current_vci, 2),
            pct_good=round(current_vci * 0.4, 1), # Mock split
            pct_fair=round(current_vci * 0.4, 1),
            pct_poor=round(current_vci * 0.2, 1),
            total_maintenance_cost=round(annual_budget, 2),
            asset_value=0 
        ))
        
        # Inflate budget for next year
        annual_budget *= (1 + inflation)

    return SimulationOutput(
        project_id=str(project_id),
        year_count=duration,
        yearly_data=yearly_results,
        total_cost_npv=sum(y.total_maintenance_cost for y in yearly_results),
        final_network_condition=yearly_results[-1].avg_condition_index
    )