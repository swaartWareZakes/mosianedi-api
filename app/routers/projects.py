from fastapi import APIRouter, HTTPException, Depends, Header
from decimal import Decimal
import os
import psycopg2
from contextlib import contextmanager
from jose import jwt, JWTError
from uuid import UUID  # <--- THIS WAS MISSING

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
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], options={"verify_aud": False})
        return payload.get("sub")
    except:
        raise HTTPException(401, "Invalid token")

@router.post("/", status_code=201)
async def create_project(metadata: ProjectMetadata, user_id: str = Depends(get_current_user_id)):
    sql = """
        INSERT INTO public.projects 
        (user_id, project_name, description, start_year, forecast_duration, discount_rate)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, created_at;
    """

    data = (
        user_id,
        metadata.project_name,
        metadata.description,
        metadata.start_year,
        metadata.forecast_duration,
        Decimal(str(metadata.discount_rate)),
    )

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, data)
            project_id, created_at = cur.fetchone()
            conn.commit()

    return {
        "project_id": str(project_id),
        "message": "Project created",
        "created_at": created_at.isoformat(),
    }
    
@router.get(
    "/{project_id}",
    response_model=ProjectDB,
    summary="Get details of a specific project",
)
def get_project(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    sql = """
        SELECT * FROM public.projects
        WHERE id = %s AND user_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
                
            # Convert row to dict
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))
        
        

@router.get("/", response_model=list[ProjectDB])
async def list_projects(user_id: str = Depends(get_current_user_id)):
    sql = """
        SELECT id, user_id, project_name, description, start_year, forecast_duration, 
               discount_rate, created_at, updated_at
        FROM public.projects
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            columns = [c[0] for c in cur.description]
            rows = cur.fetchall()

    projects = []
    for row in rows:
        d = dict(zip(columns, row))
        if isinstance(d["discount_rate"], Decimal):
            d["discount_rate"] = float(d["discount_rate"])
        projects.append(d)

    return projects