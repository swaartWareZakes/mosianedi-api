# app/master_data/router.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.db.schemas import MasterDataUploadStatus
from app.routers.projects import get_current_user_id
from .schemas import DataPreviewResponse
from . import service

router = APIRouter()


# POST /api/v1/projects/{project_id}/master-data/upload
@router.post(
    "/{project_id}/master-data/upload",
    response_model=MasterDataUploadStatus,
)
async def upload_master_data(
    project_id: UUID,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    return await service.upload_master_data_service(
        project_id=project_id,
        user_id=user_id,
        upload_file=file,
    )


# GET /api/v1/projects/{project_id}/master-data/last-upload
@router.get(
    "/{project_id}/master-data/last-upload",
    response_model=MasterDataUploadStatus,
)
async def get_last_master_data_upload(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_last_master_data_upload_service(project_id, user_id)


# ✅ History: list all uploads for this project+user
@router.get(
    "/{project_id}/master-data/uploads",
    response_model=List[MasterDataUploadStatus],
)
async def get_all_master_data_uploads(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_all_master_data_uploads_service(project_id, user_id)


# GET /api/v1/projects/{project_id}/master-data/preview  (latest file)
@router.get(
    "/{project_id}/master-data/preview",
    response_model=DataPreviewResponse,
)
async def get_master_data_preview_latest(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_master_data_preview_latest_service(project_id, user_id)


# ✅ Preview a specific upload by ID (history picker)
@router.get(
    "/{project_id}/master-data/uploads/{upload_id}/preview",
    response_model=DataPreviewResponse,
)
async def get_master_data_preview_by_upload(
    project_id: UUID,
    upload_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    return service.get_master_data_preview_by_upload_service(
        project_id, upload_id, user_id
    )