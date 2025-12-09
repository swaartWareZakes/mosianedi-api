# app/master_data/repository.py
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import psycopg2
from psycopg2.extras import Json

from app.routers.projects import get_db_connection


def insert_master_data_upload(
    project_id: UUID,
    user_id: str,
    original_filename: str,
    mime_type: str,
    file_size: int,
    storage_strategy: str,
    file_bytes: bytes,
    status: str,
    row_count: Optional[int],
    validation_errors: Optional[Dict[str, Any]],
    workbook_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Insert a new row into master_data_uploads and return the record.

    workbook_payload:
        Parsed multi-sheet workbook (segments, costs, iri, etc.) stored as JSONB.
        Can be None for simple CSV uploads.
    """
    sql = """
        INSERT INTO public.master_data_uploads (
            project_id, user_id,
            original_filename, mime_type, file_size,
            storage_strategy, file_blob,
            status, row_count, validation_errors,
            workbook_payload
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING
            id, project_id, user_id,
            original_filename, mime_type, file_size,
            status, row_count, validation_errors, created_at;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    str(project_id),
                    user_id,
                    original_filename,
                    mime_type,
                    file_size,
                    storage_strategy,
                    psycopg2.Binary(file_bytes),
                    status,
                    row_count,
                    Json(validation_errors) if validation_errors else None,
                    Json(workbook_payload) if workbook_payload else None,
                ),
            )
            row = cur.fetchone()
            columns = [d[0] for d in cur.description]
            record = dict(zip(columns, row))
            conn.commit()
            return record


def fetch_last_master_data_upload(
    project_id: UUID,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the latest upload for a project+user, or None.
    """
    sql = """
        SELECT
            id, project_id, user_id,
            original_filename, mime_type, file_size,
            status, row_count, validation_errors, created_at
        FROM public.master_data_uploads
        WHERE project_id = %s AND user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                return None
            columns = [d[0] for d in cur.description]
            return dict(zip(columns, row))


def fetch_all_master_data_uploads(
    project_id: UUID,
    user_id: str,
) -> List[Dict[str, Any]]:
    """
    Return all uploads (history) for a project+user, newest → oldest.
    """
    sql = """
        SELECT
            id, project_id, user_id,
            original_filename, mime_type, file_size,
            status, row_count, validation_errors, created_at
        FROM public.master_data_uploads
        WHERE project_id = %s AND user_id = %s
        ORDER BY created_at DESC;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            rows = cur.fetchall()
            if not rows:
                return []
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in rows]


def fetch_upload_blob_latest(
    project_id: UUID,
    user_id: str,
) -> Optional[Tuple[bytes, str]]:
    """
    Return (file_bytes, filename) for the latest upload, or None.
    """
    sql = """
        SELECT file_blob, original_filename
        FROM public.master_data_uploads
        WHERE project_id = %s AND user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                return None

            file_blob_raw, filename = row
            file_bytes = (
                file_blob_raw.tobytes()
                if isinstance(file_blob_raw, memoryview)
                else file_blob_raw
            )
            return file_bytes, filename


def fetch_upload_blob_by_id(
    project_id: UUID,
    upload_id: UUID,
    user_id: str,
) -> Optional[Tuple[bytes, str]]:
    """
    Return (file_bytes, filename) for a specific upload, or None.
    """
    sql = """
        SELECT file_blob, original_filename
        FROM public.master_data_uploads
        WHERE id = %s AND project_id = %s AND user_id = %s
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(upload_id), str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                return None

            file_blob_raw, filename = row
            file_bytes = (
                file_blob_raw.tobytes()
                if isinstance(file_blob_raw, memoryview)
                else file_blob_raw
            )
            return file_bytes, filename