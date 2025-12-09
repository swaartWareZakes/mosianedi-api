# app/computation/engine.py

import pandas as pd
import numpy as np
from uuid import UUID
from app.scenarios.schemas import RonetParameters
from .schemas import SimulationOutput, YearlyResult

def run_ronet_simulation(
    project_id: UUID,
    scenario_id: UUID,
    segments_df: pd.DataFrame,
    costs_df: pd.DataFrame,
    iri_defaults_df: pd.DataFrame,
    params: RonetParameters
) -> SimulationOutput:
    
    # --- 1. PREPARE LOOKUPS ---
    # Convert CSV data into easy-to-use dictionaries
    
    # Thresholds: (Road Class, Surface) -> { good_max, poor_min }
    threshold_map = {} 
    if not iri_defaults_df.empty:
        for _, row in iri_defaults_df.iterrows():
            # Safely handle string conversion and casing
            r_class = str(row.get('road_class', '')).strip().lower()
            s_type = str(row.get('surface_type', '')).strip().lower()
            key = (r_class, s_type)
            
            threshold_map[key] = {
                'good': float(row.get('iri_good_max', 2.5)),
                'poor': float(row.get('iri_poor_min', 6.0))
            }

    # Costs: (Treatment, Surface) -> { cost, reset_iri }
    cost_map = {}
    if not costs_df.empty:
        for _, row in costs_df.iterrows():
            t_type = str(row.get('treatment', '')).strip().lower()
            s_type = str(row.get('surface_type', '')).strip().lower()
            cost_map[(t_type, s_type)] = {
                'cost': float(row.get('cost_per_km', 0)),
                'reset_iri': float(row.get('reset_to_iri', 2.0))
            }

    # --- 2. INITIALIZE NETWORK STATE ---
    # Work on a copy so we don't mutate original data
    current_segments = segments_df.copy()
    
    # Ensure numeric types and handle missing values
    current_segments['iri'] = pd.to_numeric(current_segments['iri'], errors='coerce').fillna(4.0)
    current_segments['length_km'] = pd.to_numeric(current_segments['length_km'], errors='coerce').fillna(1.0)
    current_segments['aadt'] = pd.to_numeric(current_segments.get('aadt', 0), errors='coerce').fillna(0)

    yearly_results = []
    
    # Deterioration Rates (Simplified for Prototype)
    DETERIORATION_PAVED = 0.12
    DETERIORATION_GRAVEL = 0.25

    # --- 3. SIMULATION LOOP (YEAR BY YEAR) ---
    # Loop exactly the number of years specified by the slider
    for year in range(1, params.analysis_duration + 1):
        
        year_total_cost_needed = 0
        year_total_cost_spent = 0
        
        # Track potential interventions
        interventions = [] # List of dicts

        # --- A. DETERMINE NEEDS (Unconstrained) ---
        for idx, seg in current_segments.iterrows():
            r_class = str(seg.get('road_class', '')).strip().lower()
            s_type = str(seg.get('surface_type', '')).strip().lower()
            iri = seg['iri']
            length = seg['length_km']
            
            # Get Thresholds (Default to 3.0/6.0 if not found)
            limits = threshold_map.get((r_class, s_type), {'good': 3.0, 'poor': 6.0})
            
            # 1. Deteriorate (Roads get older/rougher)
            det_rate = DETERIORATION_GRAVEL if 'gravel' in s_type else DETERIORATION_PAVED
            iri += det_rate
            
            # 2. Decision Logic (Based on Policy Bias)
            treatment_needed = None
            
            if params.policy_bias == "preventive":
                # Fix as soon as it leaves "Good" condition
                if iri > limits['good']: 
                    treatment_needed = "periodic reseal" if 'paved' in s_type else "regravelling"
            
            elif params.policy_bias == "reactive":
                # Fix only when it reaches "Poor" condition
                if iri > limits['poor']: 
                    treatment_needed = "rehabilitation" if 'paved' in s_type else "regravelling"
            
            else: # "balanced"
                if iri > limits['poor']:
                    treatment_needed = "rehabilitation" if 'paved' in s_type else "regravelling"
                elif iri > limits['good']:
                    # Only do lighter fix if we are strictly in Fair (and not Poor)
                    treatment_needed = "periodic reseal" if 'paved' in s_type else "blading"

            # 3. Calculate Cost if treatment is needed
            if treatment_needed:
                cost_info = cost_map.get((treatment_needed, s_type))
                
                # Fallback costs if CSV lookup fails
                if not cost_info:
                    if "reseal" in treatment_needed: cost_info = {'cost': 900000, 'reset_iri': 2.2}
                    elif "rehab" in treatment_needed: cost_info = {'cost': 3500000, 'reset_iri': 1.5}
                    elif "regravel" in treatment_needed: cost_info = {'cost': 600000, 'reset_iri': 4.0}
                    else: cost_info = {'cost': 50000, 'reset_iri': iri - 0.5}

                cost = cost_info['cost'] * length
                reset_iri = cost_info['reset_iri']
                
                year_total_cost_needed += cost
                interventions.append({
                    'idx': idx,
                    'cost': cost,
                    'reset_iri': reset_iri,
                    'current_iri': iri
                })
            
            # Temporarily save deteriorated state (will be overwritten if fixed)
            current_segments.at[idx, 'iri'] = iri

        # --- B. APPLY BUDGET CONSTRAINT ---
        # 100% means we spend exactly what is needed. <100% means we cut projects.
        budget_factor = params.budget_percent_baseline / 100.0
        available_budget = year_total_cost_needed * budget_factor
        
        # Sort interventions by AADT (High traffic gets priority funding)
        interventions.sort(key=lambda x: current_segments.at[x['idx'], 'aadt'], reverse=True)
        
        for action in interventions:
            if available_budget >= action['cost']:
                # Fund the project
                available_budget -= action['cost']
                year_total_cost_spent += action['cost']
                # Apply improvement (reset IRI)
                current_segments.at[action['idx'], 'iri'] = action['reset_iri']
            else:
                # No budget -> Road stays deteriorated
                pass

        # --- C. CALCULATE YEARLY STATS ---
        total_len = current_segments['length_km'].sum()
        if total_len == 0: total_len = 1 # Avoid division by zero
        
        # Weighted Average IRI
        avg_iri = (current_segments['iri'] * current_segments['length_km']).sum() / total_len
        
        # Calculate Condition Buckets
        good_km, fair_km, poor_km = 0, 0, 0
        
        for _, seg in current_segments.iterrows():
            r_class = str(seg.get('road_class', '')).strip().lower()
            s_type = str(seg.get('surface_type', '')).strip().lower()
            limits = threshold_map.get((r_class, s_type), {'good': 3.0, 'poor': 6.0})
            
            if seg['iri'] <= limits['good']: good_km += seg['length_km']
            elif seg['iri'] <= limits['poor']: fair_km += seg['length_km']
            else: poor_km += seg['length_km']

        yearly_results.append(YearlyResult(
            year=year,
            avg_condition_index=round(avg_iri, 2),
            pct_good=round((good_km / total_len) * 100, 1),
            pct_fair=round((fair_km / total_len) * 100, 1),
            pct_poor=round((poor_km / total_len) * 100, 1),
            total_maintenance_cost=round(year_total_cost_spent, 2),
            asset_value=0 # Placeholder for advanced asset value logic
        ))

    return SimulationOutput(
        project_id=str(project_id),
        scenario_id=str(scenario_id),
        year_count=params.analysis_duration,
        yearly_data=yearly_results,
        total_cost_npv=sum(y.total_maintenance_cost for y in yearly_results),
        final_network_condition=yearly_results[-1].avg_condition_index
    )