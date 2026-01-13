from uuid import UUID
from fastapi import APIRouter, Depends

from app.routers.projects import get_current_user_id
from .service import get_network_snapshot
from .schemas import NetworkSnapshotResponse

router = APIRouter()


@router.get(
    "/{project_id}/network/snapshot",
    response_model=NetworkSnapshotResponse,
    summary="Get network snapshot derived from proposal data",
)
def read_network_snapshot(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """
    New flow:
    - Snapshot is derived from captured proposal inputs (proposal_data)
    - No master_data uploads
    - No Excel parsing
    """
    return get_network_snapshot(project_id=project_id, user_id=user_id)