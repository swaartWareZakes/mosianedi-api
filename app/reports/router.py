from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List

from app.routers.projects import get_current_user_id
from .schemas import ReportCreate, ReportOut
from . import repository

router = APIRouter()


# -----------------------------------------------------------------------------
# 1) CREATE REPORT
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/reports",
    response_model=ReportOut,
    summary="Create a new Report Bundle (links simulation + optional AI)",
)
def create_new_report(
    project_id: UUID,
    payload: ReportCreate,
    user_id: str = Depends(get_current_user_id),
):
    try:
        return repository.create_report(project_id, user_id, payload.model_dump())
    except ValueError as e:
        # ownership / not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create report: {str(e)}")


# -----------------------------------------------------------------------------
# 2) LIST REPORTS (history)
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/reports",
    response_model=List[ReportOut],
    summary="List all reports for this project",
)
def list_project_reports(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    try:
        return repository.list_reports(project_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -----------------------------------------------------------------------------
# 3) VIEW REPORT (secure)
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/reports/{report_id}",
    response_model=ReportOut,
    summary="Get full report details (secure)",
)
def get_report_details(
    project_id: UUID,
    report_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    # Enforce ownership via list_reports check pattern
    try:
        # ownership check
        repository.list_reports(project_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = repository.get_full_report_data(report_id)
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")

    # Ensure report belongs to the provided project_id
    if str(data["project_id"]) != str(project_id):
        raise HTTPException(status_code=404, detail="Report not found in this project")

    return data


# -----------------------------------------------------------------------------
# 4) PUBLIC VIEW (Treasury link)
# -----------------------------------------------------------------------------
@router.get(
    "/public/view/{slug}",
    response_model=ReportOut,
    tags=["Public Reports"],
    summary="Read-only report view for external stakeholders",
)
def get_public_report(slug: str):
    report_id = repository.get_report_id_by_slug(slug)
    if not report_id:
        raise HTTPException(status_code=404, detail="Report link invalid or expired")

    data = repository.get_full_report_data(report_id)
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")

    return data