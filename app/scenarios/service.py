from uuid import UUID
from fastapi import HTTPException
from . import repository as repo
from .schemas import ForecastParametersOut, ForecastParametersPatch

def get_forecast(project_id: UUID, user_id: str) -> ForecastParametersOut:
    # 1. Ensure DB row exists (Lazy Creation)
    repo.ensure_assumptions_row(project_id, user_id)
    
    # 2. Fetch
    data = repo.get_forecast_params(project_id, user_id)
    if not data:
        raise HTTPException(404, "Forecast parameters not found")
        
    return ForecastParametersOut(**data)

def update_forecast(project_id: UUID, user_id: str, payload: ForecastParametersPatch) -> ForecastParametersOut:
    # 1. Ensure DB row exists
    repo.ensure_assumptions_row(project_id, user_id)
    
    # 2. Update
    data = payload.model_dump(exclude_unset=True)
    updated = repo.update_forecast_params(project_id, user_id, data)
    
    if not updated:
        raise HTTPException(500, "Failed to update parameters")
        
    return ForecastParametersOut(**updated)