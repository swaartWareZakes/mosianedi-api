from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

FuelOption = Literal[1, 2]

class ProposalDataPayload(BaseModel):
    # PAVED (lane-km)
    paved_arid: float = Field(0, ge=0)
    paved_semi_arid: float = Field(0, ge=0)
    paved_dry_sub_humid: float = Field(0, ge=0)
    paved_moist_sub_humid: float = Field(0, ge=0)
    paved_humid: float = Field(0, ge=0)

    # GRAVEL (lane-km)
    gravel_arid: float = Field(0, ge=0)
    gravel_semi_arid: float = Field(0, ge=0)
    gravel_dry_sub_humid: float = Field(0, ge=0)
    gravel_moist_sub_humid: float = Field(0, ge=0)
    gravel_humid: float = Field(0, ge=0)

    # Indicators (no year references)
    avg_vci_used: float = Field(0, ge=0)
    vehicle_km: float = Field(0, ge=0)
    pct_vehicle_km_used: float = Field(0, ge=0, le=100)

    fuel_sales: float = Field(0, ge=0)
    pct_fuel_sales_used: float = Field(0, ge=0, le=100)

    fuel_option_selected: FuelOption = 1
    target_vci: float = Field(45, ge=0)

    notes: Optional[str] = None
    extra_inputs: Dict[str, Any] = {}

class ProposalDataResponse(BaseModel):
    project_id: str
    user_id: str
    paved_total_lane_km: float
    gravel_total_lane_km: float
    total_lane_km: float
    payload: ProposalDataPayload
    updated_at: Optional[str] = None
