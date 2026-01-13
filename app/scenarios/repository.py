from uuid import UUID
from typing import Dict, Any, Optional
from app.routers.projects import get_db_connection

def ensure_assumptions_row(project_id: UUID, user_id: str) -> None:
    """
    Ensures a row exists for this project in the assumptions table.
    """
    sql = """
        INSERT INTO public.scenario_assumptions (project_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT (project_id) DO NOTHING;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
        conn.commit()

def get_forecast_params(project_id: UUID, user_id: str) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT 
            id, project_id, updated_at,
            analysis_duration, discount_rate,
            cpi_percentage, previous_allocation,
            paved_deterioration_rate, gravel_loss_rate, climate_stress_factor
        FROM public.scenario_assumptions
        WHERE project_id = %s AND user_id = %s
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))

def update_forecast_params(project_id: UUID, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Dynamic SQL construction
    set_clauses = []
    values = []
    for k, v in data.items():
        set_clauses.append(f"{k} = %s")
        values.append(v)
    
    if not set_clauses:
        return get_forecast_params(project_id, user_id)

    sql = f"""
        UPDATE public.scenario_assumptions
        SET {", ".join(set_clauses)}, updated_at = NOW()
        WHERE project_id = %s AND user_id = %s
        RETURNING 
            id, project_id, updated_at,
            analysis_duration, discount_rate,
            cpi_percentage, previous_allocation,
            paved_deterioration_rate, gravel_loss_rate, climate_stress_factor
    """
    
    values.extend([str(project_id), user_id])
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            row = cur.fetchone()
            conn.commit()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))