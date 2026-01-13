from pydantic import BaseModel
from typing import Dict, Any, Optional


class SnapshotProject(BaseModel):
    id: str
    project_name: str
    province: str
    start_year: int
    proposal_title: Optional[str] = None
    proposal_status: Optional[str] = None


class ClimateCategory(BaseModel):
    arid: float
    semi_arid: float
    dry_sub_humid: float
    moist_sub_humid: float
    humid: float
    total: float


class ClimateBreakdown(BaseModel):
    paved: ClimateCategory
    gravel: ClimateCategory
    network_total: float


class Indicators(BaseModel):
    avg_vci_used: float
    vehicle_km: float
    pct_vehicle_km_used: float
    fuel_sales: float
    pct_fuel_sales_used: float
    fuel_option_selected: int
    target_vci: float
    extra_inputs: Dict[str, Any]


class NetworkSnapshotPayload(BaseModel):
    status: str
    message: str
    climate_breakdown: ClimateBreakdown
    indicators: Indicators


class NetworkSnapshotResponse(BaseModel):
    project: SnapshotProject
    snapshot: NetworkSnapshotPayload