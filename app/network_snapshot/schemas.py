# app/network_snapshot/schemas.py

from uuid import UUID
from typing import List, Optional

from pydantic import BaseModel, Field


class LengthByCategory(BaseModel):
    label: str
    length_km: float


class AssetValueByCategory(BaseModel):
    label: str
    value: float


class UnitCostByCategory(BaseModel):
    label: str
    cost_per_km: float


class NetworkSnapshot(BaseModel):
    project_id: UUID
    upload_id: UUID

    # --- Core from segments sheet ---
    total_length_km: float
    total_segments: int
    total_roads: Optional[int] = None

    length_by_road_class: List[LengthByCategory] = Field(default_factory=list)
    length_by_surface_type: List[LengthByCategory] = Field(default_factory=list)

    # --- From network_length sheet (optional) ---
    total_network_length_km: Optional[float] = None
    length_by_network_type: List[LengthByCategory] = Field(default_factory=list)

    # --- From asset_value sheet (optional) ---
    total_asset_value: Optional[float] = None
    asset_value_by_category: List[AssetValueByCategory] = Field(default_factory=list)

    # --- From road_costs sheet (optional) ---
    unit_costs_by_surface: List[UnitCostByCategory] = Field(default_factory=list)