from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from uuid import UUID
from app.db.schemas import ProjectMetadata, ProjectDB
from app.dependencies import get_db_connection, get_user_context, UserContext

router = APIRouter()

def _row_to_dict(cur, row) -> Dict[str, Any]:
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))

# --- LIST PROJECTS (Role Aware) ---
@router.get("/", response_model=List[ProjectDB])
def list_projects(ctx: UserContext = Depends(get_user_context)):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if ctx.role == 'treasury':
                # Treasury sees submitted work from ALL users
                sql = """
                    SELECT id, user_id, project_name, province, start_year, status, proposal_title, proposal_status, created_at, updated_at
                    FROM public.projects
                    WHERE status IN ('submitted', 'approved', 'rejected')
                    ORDER BY updated_at DESC
                """
                cur.execute(sql)
            else:
                # Engineers see ONLY their own work
                sql = """
                    SELECT id, user_id, project_name, province, start_year, status, proposal_title, proposal_status, created_at, updated_at
                    FROM public.projects
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                """
                cur.execute(sql, (ctx.user_id,))
            
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]

# --- CREATE PROJECT (Atomic) ---
@router.post("/", status_code=201)
def create_project(metadata: ProjectMetadata, ctx: UserContext = Depends(get_user_context)):
    # 1. Project Header
    sql_project = """
        INSERT INTO public.projects (user_id, project_name, province, start_year, status, locked)
        VALUES (%s, %s, %s, %s, 'draft', false)
        RETURNING id, created_at;
    """
    # 2. Default Inputs (So Step 1 of Wizard has data)
    sql_proposal = "INSERT INTO public.proposal_data (project_id, user_id, data_source) VALUES (%s, %s, 'manual')"
    
    # 3. Default Assumptions (So Step 3 of Wizard has data)
    sql_assumptions = "INSERT INTO public.scenario_assumptions (project_id, user_id) VALUES (%s, %s)"

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                # A. Create Project
                cur.execute(sql_project, (ctx.user_id, metadata.project_name, metadata.province, metadata.start_year))
                row = cur.fetchone()
                project_id, created_at = row
                
                # B. Initialize Inputs (Proposal Data)
                cur.execute(sql_proposal, (str(project_id), ctx.user_id))

                # C. Initialize Scenarios (Assumptions)
                cur.execute(sql_assumptions, (str(project_id), ctx.user_id))
                
                # D. Log it
                cur.execute("""
                    INSERT INTO public.project_activity_log (project_id, user_id, action_type, details)
                    VALUES (%s, %s, 'create', '{}')
                """, (str(project_id), ctx.user_id))
                
            conn.commit() # Only commit if ALL steps succeed
        except Exception as e:
            conn.rollback() # If any step fails, undo everything
            raise HTTPException(status_code=500, detail=f"Failed to initialize project: {str(e)}")

    return {"id": str(project_id), "message": "Project initialized", "created_at": created_at.isoformat()}

# --- GET PROJECT ---
@router.get("/{project_id}", response_model=ProjectDB)
def get_project(project_id: UUID, ctx: UserContext = Depends(get_user_context)):
    sql = """
        SELECT id, user_id, project_name, province, start_year, status, proposal_title, proposal_status, created_at, updated_at
        FROM public.projects
        WHERE id = %s
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id),))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Project not found")
            
            data = _row_to_dict(cur, row)
            
            # Security Check
            is_owner = str(data['user_id']) == ctx.user_id
            is_treasury_viewable = ctx.role == 'treasury' and data['status'] != 'draft'
            
            if not (is_owner or is_treasury_viewable):
                raise HTTPException(403, "Access denied")

            return data

# --- DELETE PROJECT ---
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: UUID, ctx: UserContext = Depends(get_user_context)):
    sql_check = "SELECT status, locked FROM public.projects WHERE id = %s AND user_id = %s"
    sql_delete = "DELETE FROM public.projects WHERE id = %s"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_check, (str(project_id), ctx.user_id))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(404, "Project not found or permission denied.")
            
            status, locked = row
            if locked:
                raise HTTPException(400, "Cannot delete a locked/submitted project.")

            cur.execute(sql_delete, (str(project_id),))
            conn.commit()

    return