# app/master_data/service.py
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile

from app.db.schemas import MasterDataUploadStatus
from .schemas import DataPreviewResponse
from .validation import (
    parse_master_data_file,
    parse_master_workbook,
    validate_flat_segments_df,
    validate_segments_sheet,
)
from . import repository


async def upload_master_data_service(
    project_id: UUID,
    user_id: str,
    upload_file: UploadFile,
) -> MasterDataUploadStatus:
    """
    Orchestrates upload + validation + workbook parsing + persistence.

    - For Excel workbooks:
        * parse all relevant sheets into workbook_payload (JSON)
        * validate the 'segments' sheet
    - For CSV:
        * treat the flat table as the segments sheet
        * optionally still store it in workbook_payload["segments"]
    """
    file_bytes = await upload_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    mime_type = upload_file.content_type or "application/octet-stream"
    file_size = len(file_bytes)
    original_filename = upload_file.filename or "uploaded_file"
    name_lower = original_filename.lower()

    status: str
    row_count: Optional[int]
    validation_errors: Dict[str, Any]
    workbook_payload: Optional[Dict[str, Any]] = None

    try:
        # -------- Excel workbook path --------
        if name_lower.endswith((".xlsx", ".xls")):
            # Parse full workbook into JSON-friendly payload
            workbook_payload = parse_master_workbook(file_bytes, original_filename)

            # Validate the segments sheet from that payload
            status, row_count, validation_errors = validate_segments_sheet(
                workbook_payload
            )

        # -------- CSV / flat table path --------
        else:
            df = parse_master_data_file(file_bytes, original_filename)
            status, row_count, validation_errors = validate_flat_segments_df(df)

            # Optionally store the CSV as a "segments" sheet in the payload
            df_norm = df.fillna("")
            df_norm.columns = [str(c).strip().lower() for c in df_norm.columns]
            workbook_payload = {
                "segments": df_norm.to_dict(orient="records"),
            }

    except HTTPException as exc:
        # Parsing/format errors – treat as failed but still store file & error
        status = "failed"
        row_count = None
        validation_errors = {
            "parsing_error": getattr(exc, "detail", None)
            or "File could not be parsed."
        }
        workbook_payload = None

    except Exception as e:
        status = "failed"
        row_count = None
        validation_errors = {
            "validation_exception": f"Unexpected error during validation: {str(e)}"
        }
        workbook_payload = None

    # ---- PERSIST ----
    record = repository.insert_master_data_upload(
        project_id=project_id,
        user_id=user_id,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
        storage_strategy="inline",
        file_bytes=file_bytes,
        status=status,
        row_count=row_count,
        validation_errors=validation_errors if validation_errors else None,
        # Store parsed workbook JSON (if any)
        workbook_payload=workbook_payload if workbook_payload else None,
    )

    return MasterDataUploadStatus(**record)


def get_last_master_data_upload_service(
    project_id: UUID,
    user_id: str,
) -> MasterDataUploadStatus:
    record = repository.fetch_last_master_data_upload(project_id, user_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail="No master data uploads found for this project.",
        )
    return MasterDataUploadStatus(**record)


def get_all_master_data_uploads_service(
    project_id: UUID,
    user_id: str,
) -> List[MasterDataUploadStatus]:
    rows = repository.fetch_all_master_data_uploads(project_id, user_id)
    return [MasterDataUploadStatus(**r) for r in rows]


def _preview_from_blob(file_bytes: bytes, filename: str) -> DataPreviewResponse:
    """
    Preview helper: parses the first sheet / CSV file and returns the first 50 rows.
    """
    df = parse_master_data_file(file_bytes, filename)
    total_rows = len(df.index)
    preview_df = df.head(50).fillna("")
    preview_data = preview_df.to_dict("records")
    return DataPreviewResponse(
        preview_data=preview_data,
        total_rows=total_rows,
        columns=list(df.columns),
    )


def get_master_data_preview_latest_service(
    project_id: UUID,
    user_id: str,
) -> DataPreviewResponse:
    blob = repository.fetch_upload_blob_latest(project_id, user_id)
    if not blob:
        raise HTTPException(
            status_code=404,
            detail="No master data upload file found for this project.",
        )
    file_bytes, filename = blob
    if not file_bytes:
        raise HTTPException(
            status_code=500,
            detail="File blob was empty after retrieval.",
        )
    return _preview_from_blob(file_bytes, filename)


def get_master_data_preview_by_upload_service(
    project_id: UUID,
    upload_id: UUID,
    user_id: str,
) -> DataPreviewResponse:
    blob = repository.fetch_upload_blob_by_id(project_id, upload_id, user_id)
    if not blob:
        raise HTTPException(
            status_code=404,
            detail="Upload not found for preview.",
        )
    file_bytes, filename = blob
    if not file_bytes:
        raise HTTPException(
            status_code=500,
            detail="File blob was empty after retrieval.",
        )
    return _preview_from_blob(file_bytes, filename)