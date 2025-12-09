# app/dashboards/router.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends

from app.routers.projects import get_current_user_id
from .schemas import DashboardCreate, DashboardOut, DashboardUpdate
from . import service

router = APIRouter()


@router.get(
    "/{project_id}/dashboards",
    response_model=List[DashboardOut],
    summary="List dashboards for a project",
)
def list_dashboards(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.list_dashboards_service(project_id, user_id)


@router.post(
    "/{project_id}/dashboards",
    response_model=DashboardOut,
    summary="Create a new dashboard",
)
def create_dashboard(
    project_id: UUID,
    payload: DashboardCreate,
    user_id: str = Depends(get_current_user_id),
):
    return service.create_dashboard_service(project_id, user_id, payload)


@router.get(
    "/{project_id}/dashboards/{dashboard_id}",
    response_model=DashboardOut,
    summary="Get a single dashboard",
)
def get_dashboard(
    project_id: UUID,
    dashboard_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_dashboard_service(project_id, dashboard_id, user_id)


@router.put(
    "/{project_id}/dashboards/{dashboard_id}",
    response_model=DashboardOut,
    summary="Update an existing dashboard",
)
def update_dashboard(
    project_id: UUID,
    dashboard_id: UUID,
    payload: DashboardUpdate,
    user_id: str = Depends(get_current_user_id),
):
    return service.update_dashboard_service(project_id, dashboard_id, user_id, payload)