# app/scenarios/router.py

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status

from app.routers.projects import get_current_user_id
from .schemas import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioRead,
    ScenarioSummary,
)
from . import service

router = APIRouter()

# --- Config Page Endpoint ---
@router.get(
    "/{project_id}/scenarios/baseline",
    response_model=ScenarioRead,
    summary="Get (or create) the baseline scenario for config page"
)
def get_project_baseline(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_or_create_baseline(project_id, user_id)

# --- Standard CRUD ---

@router.post(
    "/{project_id}/scenarios",
    response_model=ScenarioRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_scenario(
    project_id: UUID,
    payload: ScenarioCreate,
    user_id: str = Depends(get_current_user_id),
):
    return service.create_scenario(project_id, user_id, payload)

@router.get(
    "/{project_id}/scenarios",
    response_model=List[ScenarioSummary],
)
def list_project_scenarios(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.list_scenarios(project_id, user_id)

@router.get(
    "/{project_id}/scenarios/{scenario_id}",
    response_model=ScenarioRead,
)
def get_project_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_scenario(project_id, scenario_id, user_id)

@router.put(
    "/{project_id}/scenarios/{scenario_id}",
    response_model=ScenarioRead,
)
def update_project_scenario(
    project_id: UUID,
    scenario_id: UUID,
    payload: ScenarioUpdate,
    user_id: str = Depends(get_current_user_id),
):
    return service.update_scenario(project_id, scenario_id, user_id, payload)