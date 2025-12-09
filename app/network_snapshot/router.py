# app/network_snapshot/router.py

from uuid import UUID
from fastapi import APIRouter, Depends

from app.routers.projects import get_current_user_id
from .schemas import NetworkSnapshot
from .service import get_network_snapshot

router = APIRouter()


@router.get(
    "/{project_id}/network/snapshot",
    response_model=NetworkSnapshot,
    summary="Get network snapshot for latest master data upload",
)
def read_network_snapshot(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """
    Returns high-level network metrics (total length, segments,
    breakdown by class and surface) computed from the latest
    master data upload for this project & user.
    """
    return get_network_snapshot(project_id=project_id, user_id=user_id)