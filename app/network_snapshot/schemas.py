from pydantic import BaseModel
from typing import Optional

class NetworkProfileOut(BaseModel):
    # The essential stats for the card
    totalLengthKm: float
    pavedLengthKm: float
    gravelLengthKm: float
    
    avgVci: float
    assetValue: float      # The big money number (CRC)
    
    totalVehicleKm: float
    fuelSales: float
    
    # Optional metadata if needed later
    generated_at: Optional[str] = None