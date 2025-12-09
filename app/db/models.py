# app/db/models.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
import os



JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"

print("JWT_SECRET loaded? ->", bool(JWT_SECRET))  


# Schema used for retrieving a saved project from the database
class ProjectDB(BaseModel):
    id: UUID
    user_id: UUID
    project_name: str
    description: Optional[str] = None
    start_year: int
    forecast_duration: int
    discount_rate: float # Numeric in PG, float in Python
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True # Allows Pydantic to read ORM objects