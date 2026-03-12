from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from uuid import UUID
import json

from app.db.schemas import ProjectMetadata, ProjectDB, ProjectOut 
from app.dependencies import get_db_connection, get_user_context, UserContext, get_current_user_id

router = APIRouter()

def _row_to_dict(cur, row) -> Dict[str, Any]:
    if not row:
        return {}
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))

# --- 1. LIST PROJECTS (Enterprise Transparent Workspace) ---
@router.get("/", response_model=List[ProjectDB])
def list_projects(ctx: UserContext = Depends(get_user_context)):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            select_cols = """
                id, user_id, project_name, province, scope, municipality, local_area, 
                route_name, start_point, end_point, route_length_km, surface_type, 
                climate_zone, route_specific_vci, route_daily_traffic, start_year, 
                status, proposal_title, proposal_status, created_at, updated_at
            """
            
            # Everyone in the workspace can SEE the projects. 
            # (The frontend UI handles locking them into Read-Only mode if they aren't the owner)
            sql = f"""
                SELECT DISTINCT {','.join(['p.' + c.strip() for c in select_cols.split(',')])}
                FROM public.projects p
                ORDER BY p.updated_at DESC
            """
            cur.execute(sql)
            
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]

# --- 2. CREATE PROJECT ---
@router.post("/", status_code=201)
def create_project(metadata: ProjectMetadata, ctx: UserContext = Depends(get_user_context)):
    sql_project = """
        INSERT INTO public.projects (
            user_id, project_name, province, scope, municipality, local_area, 
            route_name, start_point, end_point, route_length_km, surface_type, 
            climate_zone, route_specific_vci, route_daily_traffic, start_year, status, locked
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planning', false)
        RETURNING id, created_at;
    """

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql_project, (
                    ctx.user_id, metadata.project_name, metadata.province, metadata.scope,
                    metadata.municipality, metadata.local_area, metadata.route_name,
                    metadata.start_point, metadata.end_point, metadata.route_length_km,
                    metadata.surface_type, metadata.climate_zone, metadata.route_specific_vci,
                    metadata.route_daily_traffic, metadata.start_year
                ))
                row = cur.fetchone()
                project_id, created_at = row
                
                cur.execute("INSERT INTO public.proposal_data (project_id, user_id, data_source) VALUES (%s, %s, 'manual')", (str(project_id), ctx.user_id))
                cur.execute("INSERT INTO public.scenario_assumptions (project_id, user_id) VALUES (%s, %s)", (str(project_id), ctx.user_id))
                
                log_details = json.dumps({"scope": metadata.scope, "name": metadata.project_name})
                cur.execute("""
                    INSERT INTO public.project_activity_log (project_id, user_id, action_type, details)
                    VALUES (%s, %s, 'create_project', %s)
                """, (str(project_id), ctx.user_id, log_details))
                
            conn.commit()
            return {"id": str(project_id), "message": "Project initialized", "created_at": created_at.isoformat()}
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to initialize project: {str(e)}")

# --- 3. GET SINGLE PROJECT (Removed 403 Read Block) ---
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # We no longer restrict by user_id here. Anyone with the ID can view metadata.
            cur.execute("""
                SELECT * FROM public.projects WHERE id = %s 
            """, (str(project_id),))
            
            project_row = cur.fetchone()
            
            if not project_row:
                raise HTTPException(status_code=404, detail="Project not found.")
                
            return _row_to_dict(cur, project_row)

# --- 4. DELETE PROJECT (Owner Only + Lock Protection remains enforced) ---
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: UUID, ctx: UserContext = Depends(get_user_context)):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, locked FROM public.projects WHERE id = %s", (str(project_id),))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Project not found.")
            
            owner_id, locked = row
            
            # Delete operations are still strictly blocked!
            if str(owner_id) != ctx.user_id:
                raise HTTPException(status_code=403, detail="Only the project owner can delete this record.")
            
            if locked:
                raise HTTPException(status_code=400, detail="Cannot delete a locked or published project. Revert to draft first.")

            cur.execute("DELETE FROM public.projects WHERE id = %s", (str(project_id),))
            conn.commit()

    return None