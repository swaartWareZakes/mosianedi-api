from __future__ import annotations

import secrets
from uuid import UUID
from typing import List, Dict, Any, Optional

from psycopg2.extras import Json
from app.routers.projects import get_db_connection


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def _assert_project_owned(cur, project_id: UUID, user_id: str) -> None:
    cur.execute(
        "SELECT 1 FROM public.projects WHERE id = %s AND user_id = %s",
        (str(project_id), user_id),
    )
    if not cur.fetchone():
        raise ValueError("Project not found or not owned by user")


def _generate_slug_short(length: int = 12) -> str:
    """
    Generates a short URL-safe slug ~length chars.
    (token_urlsafe returns variable length; we slice.)
    """
    return secrets.token_urlsafe(16).replace("-", "").replace("_", "")[:length]


def create_report(project_id: UUID, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a report bundle that references a simulation run (and optionally an AI insight).
    Returns basic metadata + slug.
    """
    sql = """
        INSERT INTO public.reports
            (project_id, simulation_run_id, ai_insight_id, title, report_type, config, created_by, public_share_slug)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING
            id, project_id, title, report_type, status, public_share_slug, created_at;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _assert_project_owned(cur, project_id, user_id)

            # slug retry loop (handles rare collision)
            for _ in range(5):
                slug = _generate_slug_short(12)
                try:
                    cur.execute(
                        sql,
                        (
                            str(project_id),
                            str(payload.get("simulation_run_id")),
                            str(payload.get("ai_insight_id")) if payload.get("ai_insight_id") else None,
                            payload.get("title"),
                            payload.get("report_type"),
                            Json(payload.get("config") or {}),
                            user_id,
                            slug,
                        ),
                    )
                    row = cur.fetchone()
                    cols = [d[0] for d in cur.description]
                    conn.commit()
                    return dict(zip(cols, row))
                except Exception as e:
                    # If unique constraint on slug was hit, retry.
                    conn.rollback()
                    msg = str(e).lower()
                    if "public_share_slug" in msg or "duplicate key" in msg:
                        continue
                    raise

            raise RuntimeError("Could not generate a unique public_share_slug after retries.")


def list_reports(project_id: UUID, user_id: str) -> List[Dict[str, Any]]:
    sql = """
        SELECT id, project_id, title, report_type, status, public_share_slug, created_at
        FROM public.reports
        WHERE project_id = %s
        ORDER BY created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _assert_project_owned(cur, project_id, user_id)

            cur.execute(sql, (str(project_id),))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]


def get_full_report_data(report_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Report view join: Report + Project + Simulation + AI Insight (optional).
    Used by secure view and public view.
    """
    sql = """
        SELECT
            r.id, r.project_id, r.title, r.report_type, r.status, r.public_share_slug, r.created_at,
            p.project_name, p.province,
            sr.results_payload as simulation_data,
            ai.content as ai_narrative
        FROM public.reports r
        JOIN public.projects p ON r.project_id = p.id
        LEFT JOIN public.simulation_results sr ON r.simulation_run_id = sr.id
        LEFT JOIN public.ai_insights ai ON r.ai_insight_id = ai.id
        WHERE r.id = %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(report_id),))
            row = cur.fetchone()
            if not row:
                return None

            (
                rid, pid, title, rtype, status, slug, created_at,
                project_name, province,
                sim_data, ai_content
            ) = row

            return {
                "id": rid,
                "project_id": pid,
                "title": title,
                "report_type": rtype,
                "status": status,
                "public_share_slug": slug,
                "created_at": created_at,
                "simulation_data": sim_data,
                "ai_narrative": ai_content,
                "project_meta": {"name": project_name, "province": province},
            }


def get_report_id_by_slug(slug: str) -> Optional[UUID]:
    sql = "SELECT id FROM public.reports WHERE public_share_slug = %s LIMIT 1;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (slug,))
            row = cur.fetchone()
            return row[0] if row else None