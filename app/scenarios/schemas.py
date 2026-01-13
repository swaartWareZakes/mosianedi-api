from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ForecastParametersOut(BaseModel):
    id: UUID
    project_id: UUID
    
    # Section A: Economic Reality
    cpi_percentage: float = 6.0
    discount_rate: float = 8.0
    previous_allocation: float = 0
    
    # Section B: Engineering Reality
    paved_deterioration_rate: str = "Medium" # Slow, Medium, Fast
    gravel_loss_rate: float = 20.0          # mm/year
    climate_stress_factor: str = "Medium"   # Low, Medium, High
    
    # Section C: Time Machine
    analysis_duration: int = 5
    
    updated_at: datetime

class ForecastParametersPatch(BaseModel):
    cpi_percentage: Optional[float] = None
    discount_rate: Optional[float] = None
    previous_allocation: Optional[float] = None
    
    paved_deterioration_rate: Optional[str] = None
    gravel_loss_rate: Optional[float] = None
    climate_stress_factor: Optional[str] = None
    
    analysis_duration: Optional[int] = None