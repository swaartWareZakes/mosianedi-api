import pandas as pd
import numpy as np
from uuid import UUID
from datetime import datetime

from app.scenarios.schemas import ForecastParametersOut
from .schemas import SimulationOutput, YearlyResult, SimulationRunOptions

def run_ronet_simulation(
    project_id: UUID,
    params: ForecastParametersOut,
    network_profile: dict, 
    options: SimulationRunOptions
) -> SimulationOutput:
    
    yearly_results = []
    
    # 1. Determine Scope (Using new snake_case names)
    paved_km = network_profile.get("pavedLengthKm", 0) if options.include_paved else 0
    gravel_km = network_profile.get("gravelLengthKm", 0) if options.include_gravel else 0
    
    # 2. Setup Time
    duration = params.analysis_duration
    # Note: accessing .start_year_override (Python friendly)
    start_year = options.start_year_override or (datetime.now().year + 1)
    
    # 3. Setup Financials
    inflation = params.cpi_percentage / 100.0
    
    # --- ENGINEERING LOGIC ---
    base_need_paved = paved_km * 160_000 
    base_need_gravel = gravel_km * 45_000
    
    total_annual_need_today = base_need_paved + base_need_gravel
    current_vci = network_profile.get("avgVci", 50)
    current_asset_value = network_profile.get("assetValue", 0)

    # --- SIMULATION LOOP ---
    for i in range(duration):
        year = start_year + i
        
        # A. Apply Inflation
        year_inflation_factor = (1 + inflation) ** i
        nominal_cost_needed = total_annual_need_today * year_inflation_factor
        
        # B. Simulate Condition Change
        if (paved_km + gravel_km) > 0:
            # Funded
            improvement = 0.8 
            current_vci = min(100, current_vci + improvement)
            current_asset_value *= (1 + (inflation * 0.5))
        else:
            # Unfunded / Not Selected
            current_vci = max(0, current_vci - 2.5)

        yearly_results.append(YearlyResult(
            year=year,
            avg_condition_index=round(current_vci, 2),
            pct_good=round(current_vci * 0.45, 1),
            pct_fair=round(current_vci * 0.35, 1),
            pct_poor=round(current_vci * 0.20, 1),
            total_maintenance_cost=round(nominal_cost_needed, 2),
            asset_value=round(current_asset_value, 2)
        ))

    return SimulationOutput(
        project_id=str(project_id),
        year_count=duration,
        yearly_data=yearly_results,
        total_cost_npv=sum(y.total_maintenance_cost for y in yearly_results),
        final_network_condition=yearly_results[-1].avg_condition_index
    )