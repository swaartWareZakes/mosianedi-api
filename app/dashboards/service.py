# app/dashboards/service.py
from typing import List
from uuid import UUID

from fastapi import HTTPException

from .schemas import DashboardCreate, DashboardOut, DashboardUpdate
from . import repository


def list_dashboards_service(
    project_id: UUID,
    user_id: str,
) -> List[DashboardOut]:
    rows = repository.list_dashboards_for_project(project_id, user_id)
    return [DashboardOut(**r) for r in rows]


def get_dashboard_service(
    project_id: UUID,
    dashboard_id: UUID,
    user_id: str,
) -> DashboardOut:
    row = repository.fetch_dashboard(project_id, dashboard_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dashboard not found.")
    return DashboardOut(**row)


def create_dashboard_service(
    project_id: UUID,
    user_id: str,
    data: DashboardCreate,
) -> DashboardOut:
    payload = data.model_dump()
    row = repository.insert_dashboard(project_id, user_id, payload)
    return DashboardOut(**row)


def update_dashboard_service(
    project_id: UUID,
    dashboard_id: UUID,
    user_id: str,
    data: DashboardUpdate,
) -> DashboardOut:
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    row = repository.update_dashboard(project_id, dashboard_id, user_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Dashboard not found.")
    return DashboardOut(**row)