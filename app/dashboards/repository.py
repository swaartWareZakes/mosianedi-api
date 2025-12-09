# app/dashboards/repository.py
from typing import Any, Dict, List, Optional
from uuid import UUID

from psycopg2.extras import Json

from app.routers.projects import get_db_connection


def list_dashboards_for_project(
    project_id: UUID,
    user_id: str,
) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id, project_id, user_id,
            name, description, is_favorite,
            layout, overrides,
            created_at, updated_at
        FROM public.project_dashboards
        WHERE project_id = %s AND user_id = %s
        ORDER BY is_favorite DESC, created_at DESC;
    """
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (str(project_id), user_id))
        rows = cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


def fetch_dashboard(
    project_id: UUID,
    dashboard_id: UUID,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            id, project_id, user_id,
            name, description, is_favorite,
            layout, overrides,
            created_at, updated_at
        FROM public.project_dashboards
        WHERE id = %s AND project_id = %s AND user_id = %s
        LIMIT 1;
    """
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (str(dashboard_id), str(project_id), user_id))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def insert_dashboard(
    project_id: UUID,
    user_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    sql = """
        INSERT INTO public.project_dashboards (
            project_id, user_id,
            name, description, is_favorite,
            layout, overrides
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING
            id, project_id, user_id,
            name, description, is_favorite,
            layout, overrides,
            created_at, updated_at;
    """
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                str(project_id),
                user_id,
                payload.get("name"),
                payload.get("description"),
                payload.get("is_favorite", False),
                Json(payload.get("layout")) if payload.get("layout") is not None else None,
                Json(payload.get("overrides")) if payload.get("overrides") is not None else None,
            ),
        )
        row = cur.fetchone()
        cols = [d[0] for d in cur.description]
        conn.commit()
        return dict(zip(cols, row))


def update_dashboard(
    project_id: UUID,
    dashboard_id: UUID,
    user_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    sql = """
        UPDATE public.project_dashboards
        SET
            name = COALESCE(%s, name),
            description = COALESCE(%s, description),
            is_favorite = COALESCE(%s, is_favorite),
            layout = COALESCE(%s, layout),
            overrides = COALESCE(%s, overrides),
            updated_at = now()
        WHERE id = %s AND project_id = %s AND user_id = %s
        RETURNING
            id, project_id, user_id,
            name, description, is_favorite,
            layout, overrides,
            created_at, updated_at;
    """
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                payload.get("name"),
                payload.get("description"),
                payload.get("is_favorite"),
                Json(payload.get("layout")) if "layout" in payload else None,
                Json(payload.get("overrides")) if "overrides" in payload else None,
                str(dashboard_id),
                str(project_id),
                user_id,
            ),
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        conn.commit()
        return dict(zip(cols, row))