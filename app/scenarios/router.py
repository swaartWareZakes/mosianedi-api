from fastapi import APIRouter, Depends
from uuid import UUID

from app.routers.projects import get_current_user_id
from .schemas import ForecastParametersOut, ForecastParametersPatch
from . import service

router = APIRouter()

@router.get(
    "/{project_id}/forecast",
    response_model=ForecastParametersOut,
    summary="Get forecast & strategy assumptions"
)
def get_forecast_parameters(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_forecast(project_id, user_id)

@router.patch(
    "/{project_id}/forecast",
    response_model=ForecastParametersOut,
    summary="Update forecast & strategy assumptions"
)
def update_forecast_parameters(
    project_id: UUID,
    payload: ForecastParametersPatch,
    user_id: str = Depends(get_current_user_id),
):
    return service.update_forecast(project_id, user_id, payload)