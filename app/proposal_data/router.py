from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.routers.projects import get_current_user_id, get_db_connection
from .schemas import ProposalDataOut, ProposalDataPatch

router = APIRouter()

def _row_to_dict(cur, row) -> Dict[str, Any]:
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))

def _ensure_row(project_id: UUID, user_id: str) -> None:
    sql = """
        INSERT INTO public.proposal_data (project_id, user_id, data_source)
        VALUES (%s, %s, 'manual')
        ON CONFLICT (project_id) DO NOTHING;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
        conn.commit()

@router.get(
    "/{project_id}/proposal-data",
    response_model=ProposalDataOut,
    summary="Get proposal inputs for a project",
)
def get_proposal_data(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    # ensure row exists (covers old projects)
    _ensure_row(project_id, user_id)

    sql = """
        SELECT *
        FROM public.proposal_data
        WHERE project_id = %s AND user_id = %s
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "proposal_data row not found after ensure (unexpected).")
            return _row_to_dict(cur, row)

@router.patch(
    "/{project_id}/proposal-data",
    response_model=ProposalDataOut,
    summary="Update proposal inputs for a project",
)
def patch_proposal_data(
    project_id: UUID,
    payload: ProposalDataPatch,
    user_id: str = Depends(get_current_user_id),
):
    # ensure row exists (covers old projects)
    _ensure_row(project_id, user_id)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields provided")

    set_parts = []
    values = []
    for k, v in data.items():
        set_parts.append(f"{k} = %s")
        values.append(v)

    set_clause = ", ".join(set_parts)

    sql = f"""
        UPDATE public.proposal_data
        SET {set_clause}, updated_at = now()
        WHERE project_id = %s AND user_id = %s
        RETURNING *;
    """

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (*values, str(project_id), user_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, "proposal_data row not found for this project/user")
                conn.commit()
                return _row_to_dict(cur, row)
        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(500, f"Failed to update proposal_data: {str(e)}")
        