from uuid import UUID
from fastapi import APIRouter, Depends

from app.routers.projects import get_current_user_id
from .service import get_network_snapshot
from .schemas import NetworkProfileOut

router = APIRouter()

@router.get(
    "/{project_id}/network/snapshot",
    response_model=NetworkProfileOut,
    summary="Get calculated asset profile (CRC & VCI)",
)
def read_network_snapshot(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return get_network_snapshot(project_id=project_id, user_id=user_id)