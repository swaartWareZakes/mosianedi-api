# """
# Master Data Upload, Validation, History & Preview Endpoints
# ===========================================================

# Clean, modular, production-ready version.
# """

# from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
# from typing import Optional, Dict, Any, List
# from uuid import UUID
# from io import BytesIO

# import pandas as pd
# import psycopg2
# from psycopg2.extras import Json

# from pydantic import BaseModel

# # Shared helpers
# from app.routers.projects import get_db_connection, get_current_user_id
# from app.db.schemas import MasterDataUploadStatus


# # ============================================================
# # PREVIEW SCHEMAS
# # ============================================================

# class DataPreviewResponse(BaseModel):
#     preview_data: List[Dict[str, Any]]
#     total_rows: int
#     columns: List[str]


# # ============================================================
# # REQUIRED COLUMNS FOR MASTER DATA
# # ============================================================

# REQUIRED_COLUMNS = {
#     "segment_id",
#     "road_id",
#     "road_class",
#     "length_km",
#     "surface_type",
# }

# router = APIRouter()


# # ============================================================
# # HELPERS
# # ============================================================

# def _parse_master_data_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
#     """
#     Convert uploaded Excel/CSV file → pandas DataFrame.
#     """
#     buffer = BytesIO(file_bytes)
#     name = filename.lower()

#     try:
#         if name.endswith((".xlsx", ".xls")):
#             return pd.read_excel(buffer)
#         elif name.endswith(".csv"):
#             return pd.read_csv(buffer)
#         else:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid file type. Use .xlsx, .xls or .csv."
#             )
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Could not parse file: {str(e)}"
#         )


# # ============================================================
# # UPLOAD ENDPOINT
# # ============================================================

# @router.post("/{project_id}/master-data/upload", response_model=MasterDataUploadStatus)
# async def upload_master_data(
#     project_id: UUID,
#     file: UploadFile = File(...),
#     user_id: str = Depends(get_current_user_id),
# ):
#     """
#     Upload + validate a master data file.
#     Saves the file blob inline in PostgreSQL.
#     """
#     file_bytes = await file.read()
#     if not file_bytes:
#         raise HTTPException(status_code=400, detail="Uploaded file is empty.")

#     mime_type = file.content_type or "application/octet-stream"
#     file_size = len(file_bytes)

#     validation_errors: Dict[str, Any] = {}
#     status = "validated"
#     row_count: Optional[int] = None

#     # ---- VALIDATION ----
#     try:
#         df = _parse_master_data_file(file_bytes, file.filename)
#         row_count = len(df.index)

#         df_columns_lower = {c.lower(): c for c in df.columns}
#         missing = [col for col in REQUIRED_COLUMNS if col not in df_columns_lower]

#         if missing:
#             status = "failed"
#             validation_errors["missing_columns"] = missing

#     except HTTPException:
#         status = "failed"
#         raise
#     except Exception as e:
#         status = "failed"
#         validation_errors["validation_error"] = f"Unexpected: {str(e)}"

#     # ---- INSERT INTO DB ----
#     sql = """
#         INSERT INTO public.master_data_uploads (
#             project_id, user_id,
#             original_filename, mime_type, file_size,
#             storage_strategy, file_blob,
#             status, row_count, validation_errors
#         )
#         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#         RETURNING
#             id, project_id, user_id, original_filename, mime_type,
#             file_size, status, row_count, validation_errors, created_at;
#     """

#     try:
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 cur.execute(sql, (
#                     str(project_id),
#                     user_id,
#                     file.filename,
#                     mime_type,
#                     file_size,
#                     "inline",
#                     psycopg2.Binary(file_bytes),
#                     status,
#                     row_count,
#                     Json(validation_errors) if validation_errors else None
#                 ))

#                 record = dict(zip([d[0] for d in cur.description], cur.fetchone()))
#                 conn.commit()
#                 return record

#     except Exception as e:
#         print("[MASTER_DATA] Upload DB error:", e)
#         raise HTTPException(500, "Internal server error during upload.")


# # ============================================================
# # LAST UPLOAD ENDPOINT
# # ============================================================

# @router.get("/{project_id}/master-data/last-upload", response_model=MasterDataUploadStatus)
# async def get_last_master_data_upload(
#     project_id: UUID,
#     user_id: str = Depends(get_current_user_id)
# ):
#     """
#     Return metadata for the most recent upload.
#     """
#     sql = """
#         SELECT
#             id, project_id, user_id,
#             original_filename, mime_type, file_size,
#             status, row_count, validation_errors, created_at
#         FROM public.master_data_uploads
#         WHERE project_id = %s AND user_id = %s
#         ORDER BY created_at DESC
#         LIMIT 1;
#     """

#     try:
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 cur.execute(sql, (str(project_id), user_id))
#                 row = cur.fetchone()

#                 if not row:
#                     raise HTTPException(404, "No master data uploads found.")

#                 record = dict(zip([d[0] for d in cur.description], row))
#                 return record

#     except Exception as e:
#         print("[MASTER_DATA] Last upload fetch error:", e)
#         raise HTTPException(500, "Internal server error fetching last upload.")


# # ============================================================
# # PREVIEW ENDPOINT (LATEST FILE)
# # ============================================================

# @router.get("/{project_id}/master-data/preview", response_model=DataPreviewResponse)
# async def get_master_data_preview(
#     project_id: UUID,
#     user_id: str = Depends(get_current_user_id)
# ):
#     """
#     Reads the file_blobs of the most recent upload and returns 
#     up to 50 preview rows.
#     """
#     sql = """
#         SELECT file_blob, original_filename
#         FROM public.master_data_uploads
#         WHERE project_id = %s AND user_id = %s
#         ORDER BY created_at DESC
#         LIMIT 1;
#     """

#     try:
#         with get_db_connection() as conn:
#             with conn.cursor() as cur:
#                 cur.execute(sql, (str(project_id), user_id))
#                 row = cur.fetchone()

#                 if not row:
#                     raise HTTPException(404, "No file found for preview.")

#                 file_blob_raw, filename = row

#                 if isinstance(file_blob_raw, memoryview):
#                     file_bytes = file_blob_raw.tobytes()
#                 else:
#                     file_bytes = file_blob_raw

#     except Exception as e:
#         print("[PREVIEW] DB error:", e)
#         raise HTTPException(500, "Database error fetching file for preview.")

#     # ---- PARSE ----
#     try:
#         df = _parse_master_data_file(file_bytes, filename)
#         total_rows = len(df.index)

#         preview_df = df.head(50).fillna("")
#         preview_data = preview_df.to_dict("records")

#         return DataPreviewResponse(
#             preview_data=preview_data,
#             total_rows=total_rows,
#             columns=list(df.columns)
#         )
#     except Exception as e:
#         print("[PREVIEW] Pandas error:", e)
#         raise HTTPException(500, f"Error processing preview: {str(e)}")