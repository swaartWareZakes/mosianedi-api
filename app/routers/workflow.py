from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
from app.dependencies import get_db_connection, get_user_context, UserContext

router = APIRouter()

class ReviewAction(BaseModel):
    comment: str

@router.post("/{project_id}/submit")
def submit_project(project_id: UUID, ctx: UserContext = Depends(get_user_context)):
    check_sql = "SELECT status FROM public.projects WHERE id = %s AND user_id = %s"
    update_sql = "UPDATE public.projects SET status = 'submitted', locked = true, updated_at = NOW() WHERE id = %s"
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(check_sql, (str(project_id), ctx.user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Project not found.")
            
            if row[0] == 'submitted':
                 raise HTTPException(400, "Already submitted.")

            cur.execute(update_sql, (str(project_id),))
            cur.execute("INSERT INTO public.project_activity_log (project_id, user_id, action_type) VALUES (%s, %s, 'submit')", (str(project_id), ctx.user_id))
            conn.commit()

    return {"status": "submitted"}

@router.post("/{project_id}/approve")
def approve_project(project_id: UUID, payload: ReviewAction, ctx: UserContext = Depends(get_user_context)):
    if ctx.role != 'treasury': raise HTTPException(403, "Treasury only")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE public.projects SET status = 'approved', locked = true WHERE id = %s", (str(project_id),))
            cur.execute("INSERT INTO public.project_reviews (project_id, reviewer_id, status_decision, comment) VALUES (%s, %s, 'approved', %s)", (str(project_id), ctx.user_id, payload.comment))
            conn.commit()
    return {"status": "approved"}

@router.post("/{project_id}/reject")
def reject_project(project_id: UUID, payload: ReviewAction, ctx: UserContext = Depends(get_user_context)):
    if ctx.role != 'treasury': raise HTTPException(403, "Treasury only")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Unlock so engineer can fix
            cur.execute("UPDATE public.projects SET status = 'rejected', locked = false WHERE id = %s", (str(project_id),))
            cur.execute("INSERT INTO public.project_reviews (project_id, reviewer_id, status_decision, comment) VALUES (%s, %s, 'rejected', %s)", (str(project_id), ctx.user_id, payload.comment))
            conn.commit()
    return {"status": "rejected"}