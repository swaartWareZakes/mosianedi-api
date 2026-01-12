from fastapi import APIRouter, HTTPException, Depends, Header
import os
import psycopg2
from contextlib import contextmanager
from jose import jwt
from uuid import UUID

from app.db.schemas import ProjectMetadata, ProjectDB

router = APIRouter()

JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"


@contextmanager
def get_db_connection():
    DB_URL = os.getenv("DATABASE_URL")
    if not DB_URL:
        raise ValueError("DATABASE_URL missing")

    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        yield conn
    finally:
        if conn:
            conn.close()


def get_current_user_id(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(401, "Authorization header missing")
    try:
        scheme, token = authorization.split()
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(401, "Invalid token (sub missing)")
        return sub
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid token")


# -------------------------------------------------------------------
# CREATE PROJECT (Proposal container) + initialize proposal_data row
# -------------------------------------------------------------------
@router.post("/", status_code=201)
async def create_project(metadata: ProjectMetadata, user_id: str = Depends(get_current_user_id)):
    """
    Creates a project (proposal container) and immediately creates an empty proposal_data row (Option A).
    """

    sql_project = """
        INSERT INTO public.projects (user_id, project_name, province, start_year)
        VALUES (%s, %s, %s, %s)
        RETURNING id, created_at;
    """

    sql_proposal = """
        INSERT INTO public.proposal_data (project_id, user_id, data_source)
        VALUES (%s, %s, 'manual')
        ON CONFLICT (project_id) DO NOTHING;
    """

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                # 1) create project
                cur.execute(
                    sql_project,
                    (user_id, metadata.project_name, metadata.province, metadata.start_year),
                )
                project_id, created_at = cur.fetchone()

                # 2) init proposal row
                cur.execute(sql_proposal, (str(project_id), user_id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

    return {
        "project_id": str(project_id),
        "message": "Project created (proposal_data initialized)",
        "created_at": created_at.isoformat(),
    }


# -------------------------------------------------------------------
# GET ONE PROJECT
# -------------------------------------------------------------------
@router.get("/{project_id}", response_model=ProjectDB)
def get_project(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    sql = """
        SELECT
          id,
          user_id,
          project_name,
          province,
          start_year,
          proposal_title,
          proposal_status,
          created_at,
          updated_at
        FROM public.projects
        WHERE id = %s AND user_id = %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Project not found")

            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))


# -------------------------------------------------------------------
# LIST PROJECTS
# -------------------------------------------------------------------
@router.get("/", response_model=list[ProjectDB])
async def list_projects(user_id: str = Depends(get_current_user_id)):
    sql = """
        SELECT
          id,
          user_id,
          project_name,
          province,
          start_year,
          proposal_title,
          proposal_status,
          created_at,
          updated_at
        FROM public.projects
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            columns = [c[0] for c in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]