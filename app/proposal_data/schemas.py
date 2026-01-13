from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ProposalDataOut(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    data_source: str

    paved_arid: float = 0
    paved_semi_arid: float = 0
    paved_dry_sub_humid: float = 0
    paved_moist_sub_humid: float = 0
    paved_humid: float = 0

    gravel_arid: float = 0
    gravel_semi_arid: float = 0
    gravel_dry_sub_humid: float = 0
    gravel_moist_sub_humid: float = 0
    gravel_humid: float = 0

    avg_vci_used: float = 0
    vehicle_km: float = 0
    pct_vehicle_km_used: float = 0
    fuel_sales: float = 0
    pct_fuel_sales_used: float = 0
    fuel_option_selected: int = 1
    target_vci: float = 45

    extra_inputs: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class ProposalDataPatch(BaseModel):
    # allow partial updates
    paved_arid: Optional[float] = None
    paved_semi_arid: Optional[float] = None
    paved_dry_sub_humid: Optional[float] = None
    paved_moist_sub_humid: Optional[float] = None
    paved_humid: Optional[float] = None

    gravel_arid: Optional[float] = None
    gravel_semi_arid: Optional[float] = None
    gravel_dry_sub_humid: Optional[float] = None
    gravel_moist_sub_humid: Optional[float] = None
    gravel_humid: Optional[float] = None

    avg_vci_used: Optional[float] = None
    vehicle_km: Optional[float] = None
    pct_vehicle_km_used: Optional[float] = None
    fuel_sales: Optional[float] = None
    pct_fuel_sales_used: Optional[float] = None
    fuel_option_selected: Optional[int] = None
    target_vci: Optional[float] = None

    extra_inputs: Optional[Dict[str, Any]] = None
    
    