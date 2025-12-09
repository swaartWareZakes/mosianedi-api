# app/scenarios/repository.py

from uuid import UUID
from typing import List, Dict, Any, Optional

from psycopg2.extras import Json

from app.routers.projects import get_db_connection


def create_scenario(
    project_id: UUID,
    user_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    sql = """
        INSERT INTO public.project_scenarios (
            project_id, user_id,
            name, description, is_baseline, parameters
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING
            id, project_id, user_id,
            name, description, is_baseline,
            parameters, created_at, updated_at;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    str(project_id),
                    user_id,
                    payload["name"],
                    payload.get("description"),
                    payload.get("is_baseline", False),
                    Json(payload.get("parameters", {})),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(zip([d[0] for d in cur.description], row))


def list_scenarios(
    project_id: UUID,
    user_id: str,
) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id, project_id, user_id,
            name, description, is_baseline,
            parameters, created_at, updated_at
        FROM public.project_scenarios
        WHERE project_id = %s AND user_id = %s
        ORDER BY is_baseline DESC, created_at ASC;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]


def get_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            id, project_id, user_id,
            name, description, is_baseline,
            parameters, created_at, updated_at
        FROM public.project_scenarios
        WHERE project_id = %s AND id = %s AND user_id = %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), str(scenario_id), user_id))
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip([d[0] for d in cur.description], row))


def update_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Partial update; only apply fields present in payload.
    """
    fields = []
    values = []

    if "name" in payload:
        fields.append("name = %s")
        values.append(payload["name"])
    if "description" in payload:
        fields.append("description = %s")
        values.append(payload["description"])
    if "is_baseline" in payload:
        fields.append("is_baseline = %s")
        values.append(payload["is_baseline"])
    if "parameters" in payload:
        fields.append("parameters = %s")
        values.append(Json(payload["parameters"]))

    if not fields:
        return get_scenario(project_id, scenario_id, user_id)

    # updated_at
    fields.append("updated_at = now()")

    sql = f"""
        UPDATE public.project_scenarios
        SET {", ".join(fields)}
        WHERE project_id = %s AND id = %s AND user_id = %s
        RETURNING
            id, project_id, user_id,
            name, description, is_baseline,
            parameters, created_at, updated_at;
    """

    values.extend([str(project_id), str(scenario_id), user_id])

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            row = cur.fetchone()
            conn.commit()
            if not row:
                return None
            return dict(zip([d[0] for d in cur.description], row))


def delete_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str,
) -> bool:
    sql = """
        DELETE FROM public.project_scenarios
        WHERE project_id = %s AND id = %s AND user_id = %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), str(scenario_id), user_id))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted