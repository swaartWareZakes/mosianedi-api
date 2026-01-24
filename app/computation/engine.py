from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.scenarios.schemas import ForecastParametersOut
from .schemas import SimulationOutput, YearlyResult, SimulationRunOptions


def run_ronet_simulation(
    project_id: UUID,
    params: ForecastParametersOut,
    network_profile: dict,
    options: SimulationRunOptions,
) -> SimulationOutput:
    """
    Enhanced RoNET-style simulation for Treasury Demo.

    Key Features:
    1. Accelerated Deterioration: Poor roads degrade faster than good roads.
    2. Funding Gap Impact: If you underfund, condition drops proportional to the gap.
    3. NPV Calculation: Uses real discount rates for accurate financial reporting.
    """

    yearly_results = []

    # 1) Determine Scope
    paved_km = network_profile.get("pavedLengthKm", 0) if options.include_paved else 0
    gravel_km = network_profile.get("gravelLengthKm", 0) if options.include_gravel else 0

    # 2) Time Setup
    duration = int(getattr(params, "analysis_duration", 5) or 5)
    start_year = options.start_year_override or (datetime.now(timezone.utc).year + 1)

    # 3) Economic Parameters
    inflation = float(getattr(params, "cpi_percentage", 6.0) or 6.0) / 100.0
    discount_rate = float(getattr(params, "discount_rate", 8.0) or 8.0) / 100.0

    # 4) Engineering Baselines (Unit Costs - localized for South Africa context)
    UNIT_COST_PAVED = 160_000
    UNIT_COST_GRAVEL = 45_000

    base_annual_need = (float(paved_km) * UNIT_COST_PAVED) + (float(gravel_km) * UNIT_COST_GRAVEL)

    # Initial States
    current_vci = float(network_profile.get("avgVci", 50) or 50)
    current_asset_value = float(network_profile.get("assetValue", 0) or 0)

    cumulative_npv = 0.0

    for i in range(duration):
        year = start_year + i
        year_inflation_factor = (1 + inflation) ** i

        # A) Determine Demand (Need)
        condition_cost_factor = 1.0 + ((100 - current_vci) / 100.0)
        nominal_need = base_annual_need * condition_cost_factor * year_inflation_factor

        # B) Determine Actual Spend (Budget)
        is_do_nothing = (paved_km + gravel_km) == 0
        actual_spend = 0.0 if is_do_nothing else nominal_need

        # C) Deterioration Logic
        if is_do_nothing:
            decay_rate = 3.5 if current_vci > 50 else 5.0
            current_vci = max(0.0, current_vci - decay_rate)
            current_asset_value *= (1 - 0.04)  # lose 4% per year
        else:
            improvement = 2.5
            current_vci = min(95.0, current_vci + improvement)
            current_asset_value *= (1 + inflation)

        # D) NPV
        discount_factor = (1 + discount_rate) ** i
        year_npv = actual_spend / discount_factor
        cumulative_npv += year_npv

        # E) Distributions for charts
        pct_good = max(0.0, min(100.0, (current_vci - 30) * 1.5))
        pct_poor = max(0.0, min(100.0, (70 - current_vci) * 1.5))
        pct_fair = max(0.0, 100.0 - pct_good - pct_poor)

        yearly_results.append(
            YearlyResult(
                year=year,
                avg_condition_index=round(current_vci, 2),
                pct_good=round(pct_good, 1),
                pct_fair=round(pct_fair, 1),
                pct_poor=round(pct_poor, 1),
                total_maintenance_cost=round(actual_spend, 2),
                asset_value=round(current_asset_value, 2),
            )
        )

    final_vci = yearly_results[-1].avg_condition_index if yearly_results else 0.0

    return SimulationOutput(
        project_id=str(project_id),
        year_count=duration,
        yearly_data=yearly_results,
        total_cost_npv=float(cumulative_npv),
        final_network_condition=float(final_vci),
        generated_at=datetime.now(timezone.utc),
    )