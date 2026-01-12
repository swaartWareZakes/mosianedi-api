# app/network_snapshot/router.py

from uuid import UUID
from fastapi import APIRouter, Depends

from app.routers.projects import get_current_user_id
from .service import get_network_snapshot

router = APIRouter()


@router.get(
    "/{project_id}/network/snapshot",
    summary="Get network snapshot derived from proposal data",
)
def read_network_snapshot(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """
    Returns a lightweight network snapshot derived from proposal_data.

    New flow:
    - No master_data uploads
    - No Excel parsing
    - Snapshot is derived from captured proposal inputs
    """
    return get_network_snapshot(project_id=project_id, user_id=user_id)