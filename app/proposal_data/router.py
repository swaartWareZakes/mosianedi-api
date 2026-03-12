from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.dependencies import get_current_user_id, get_db_connection 
from .schemas import ProposalDataOut, ProposalDataPatch

router = APIRouter()

def _row_to_dict(cur, row) -> Dict[str, Any]:
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))

# --- HELPER: Check Write Access (Owner OR Collaborator) ---
def _has_write_access(conn, project_id: str, user_id: str) -> bool:
    with conn.cursor() as cur:
        # Check if user is owner OR is listed in collaborators for this project
        cur.execute("""
            SELECT 1 FROM public.projects p
            LEFT JOIN public.project_collaborators pc ON p.id = pc.project_id
            WHERE p.id = %s 
            AND (p.user_id = %s OR pc.user_id = %s)
        """, (project_id, user_id, user_id))
        return cur.fetchone() is not None


@router.get(
    "/{project_id}/proposal-data",
    response_model=ProposalDataOut,
    summary="Get proposal inputs for a project (Read-Only allowed)",
)
def get_proposal_data(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    with get_db_connection() as conn:
        # 1. READ BLOCK REMOVED: Anyone in the workspace can view the data.
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM public.proposal_data 
                WHERE project_id = %s
                LIMIT 1;
            """, (str(project_id),))
            row = cur.fetchone()
            
            if not row:
                # If no data exists yet, we must find the ACTUAL owner of the project
                # so we don't accidentally assign the data row to the guest viewer.
                cur.execute("SELECT user_id FROM public.projects WHERE id = %s", (str(project_id),))
                owner_row = cur.fetchone()
                if not owner_row:
                    raise HTTPException(status_code=404, detail="Project not found.")
                owner_id = owner_row[0]

                # Create default row if missing (Auto-healing)
                cur.execute("""
                    INSERT INTO public.proposal_data (project_id, user_id, data_source) 
                    VALUES (%s, %s, 'manual')
                    RETURNING *;
                """, (str(project_id), owner_id))
                conn.commit()
                row = cur.fetchone()

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
    with get_db_connection() as conn:
        # 1. Check WRITE Access (Strict Server-Side Protection)
        if not _has_write_access(conn, str(project_id), user_id):
             raise HTTPException(status_code=403, detail="Access denied. You do not have edit rights.")

        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided")

        set_parts = []
        values = []
        for k, v in data.items():
            set_parts.append(f"{k} = %s")
            values.append(v)
        
        set_clause = ", ".join(set_parts)

        # 2. Update Data
        sql = f"""
            UPDATE public.proposal_data
            SET {set_clause}, updated_at = now()
            WHERE project_id = %s
            RETURNING *;
        """

        try:
            with conn.cursor() as cur:
                cur.execute(sql, (*values, str(project_id)))
                row = cur.fetchone()
                
                # UPSERT logic: If row didn't exist, insert it now
                if not row:
                    cur.execute("""
                        INSERT INTO public.proposal_data (project_id, user_id, data_source) 
                        VALUES (%s, %s, 'manual')
                    """, (str(project_id), user_id))
                    # Re-run the update to apply the specific patches
                    cur.execute(sql, (*values, str(project_id)))
                    row = cur.fetchone()

                conn.commit()
                return _row_to_dict(cur, row)
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update proposal_data: {str(e)}")