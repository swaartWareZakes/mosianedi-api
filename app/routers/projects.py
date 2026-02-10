from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from uuid import UUID

# Ensure these imports exist in your project structure
from app.db.schemas import ProjectMetadata, ProjectDB, ProjectOut 
from app.dependencies import get_db_connection, get_user_context, UserContext, get_current_user_id

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
                # Engineers see their OWN work OR work where they are a collaborator
                sql = """
                    SELECT DISTINCT p.id, p.user_id, p.project_name, p.province, p.start_year, p.status, p.proposal_title, p.proposal_status, p.created_at, p.updated_at
                    FROM public.projects p
                    LEFT JOIN public.project_collaborators pc ON p.id = pc.project_id
                    WHERE p.user_id = %s OR pc.user_id = %s
                    ORDER BY p.updated_at DESC
                """
                cur.execute(sql, (ctx.user_id, ctx.user_id))
            
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]

# --- CREATE PROJECT ---
@router.post("/", status_code=201)
def create_project(metadata: ProjectMetadata, ctx: UserContext = Depends(get_user_context)):
    # 1. Project Header
    sql_project = """
        INSERT INTO public.projects (user_id, project_name, province, start_year, status, locked)
        VALUES (%s, %s, %s, %s, 'draft', false)
        RETURNING id, created_at;
    """
    # 2. Default Inputs
    sql_proposal = "INSERT INTO public.proposal_data (project_id, user_id, data_source) VALUES (%s, %s, 'manual')"
    
    # 3. Default Assumptions
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
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to initialize project: {str(e)}")

    return {"id": str(project_id), "message": "Project initialized", "created_at": created_at.isoformat()}

# --- GET PROJECT (Single - Fixed for Collaboration) ---
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if user is owner OR a collaborator
            cur.execute("""
                SELECT p.* FROM public.projects p
                LEFT JOIN public.project_collaborators pc ON p.id = pc.project_id
                WHERE p.id = %s 
                AND (p.user_id = %s OR pc.user_id = %s)
            """, (str(project_id), user_id, user_id))
            
            project = cur.fetchone()
            
            if not project:
                raise HTTPException(status_code=403, detail="Project not found or access denied")
                
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, project))

# --- DELETE PROJECT ---
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: UUID, ctx: UserContext = Depends(get_user_context)):
    # Check ownership (Collaborators usually CANNOT delete, only owners)
    sql_check = "SELECT status, locked FROM public.projects WHERE id = %s AND user_id = %s"
    sql_delete = "DELETE FROM public.projects WHERE id = %s"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_check, (str(project_id), ctx.user_id))
            row = cur.fetchone()
            
            if not row:
                # If row missing, check if it exists at all to give better error
                cur.execute("SELECT 1 FROM public.projects WHERE id = %s", (str(project_id),))
                if cur.fetchone():
                     raise HTTPException(status_code=403, detail="Only the project owner can delete this project.")
                raise HTTPException(status_code=404, detail="Project not found.")
            
            status, locked = row
            if locked:
                raise HTTPException(status_code=400, detail="Cannot delete a locked/submitted project.")

            cur.execute(sql_delete, (str(project_id),))
            conn.commit()

    return