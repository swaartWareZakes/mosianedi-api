from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import List
from psycopg2.extras import Json

from app.routers.projects import get_current_user_id, get_db_connection
from .service import generate_strategic_narrative
from .schemas import AiInsightOut

router = APIRouter()

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def _assert_project_owned(cur, project_id: UUID, user_id: str) -> str:
    """
    Ensures the project exists AND belongs to the authenticated user.
    Returns project_name.
    """
    cur.execute(
        """
        SELECT project_name
        FROM public.projects
        WHERE id = %s AND user_id = %s
        """,
        (str(project_id), user_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found or not owned by user.")
    return row[0]


# -----------------------------------------------------------------------------
# 1. GENERATE & SAVE (The "Create" Action)
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/advisor/generate",
    response_model=AiInsightOut,
    summary="Generate insight for the ACTIVE simulation and save it to history.",
)
def generate_and_save_ai_feedback(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """
    1) Verify project ownership
    2) Read active_simulation_run_id
    3) Pull that simulation's results_payload
    4) Generate insight via OpenAI
    5) Save to ai_insights
    6) Return the saved row + simulation_summary snippet
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # A) Ownership + fetch project_name
            project_name = _assert_project_owned(cur, project_id, user_id)

            # B) Get Active Simulation ID
            cur.execute(
                "SELECT active_simulation_run_id FROM public.projects WHERE id = %s",
                (str(project_id),),
            )
            proj_row = cur.fetchone()
            active_run_id = proj_row[0] if proj_row else None

            if not active_run_id:
                raise HTTPException(
                    status_code=400,
                    detail="No active simulation run selected. Please run a simulation first.",
                )

            # C) Fetch that run
            cur.execute(
                """
                SELECT results_payload, run_name, run_options
                FROM public.simulation_results
                WHERE id = %s AND project_id = %s
                """,
                (str(active_run_id), str(project_id)),
            )
            sim_row = cur.fetchone()
            if not sim_row:
                raise HTTPException(status_code=404, detail="Active simulation run data is missing.")

            sim_data, run_name, run_opts = sim_row
            yearly = (sim_data or {}).get("yearly_data", [])
            if not yearly:
                raise HTTPException(status_code=400, detail="Simulation payload is missing yearly_data.")

            # D) Format for AI service
            def fmt_money(x):
                if x is None:
                    return "R 0"
                try:
                    x = float(x)
                except Exception:
                    return "R 0"
                return f"R {x/1_000_000_000:.2f} Billion" if x >= 1_000_000_000 else f"R {x/1_000_000:.1f} Million"

            start_val = float(yearly[0].get("asset_value", 0) or 0)
            end_val = float(yearly[-1].get("asset_value", 0) or 0)
            start_vci = float(yearly[0].get("avg_condition_index", 0) or 0)
            end_vci = float(yearly[-1].get("avg_condition_index", 0) or 0)

            context_payload = {
                "project_name": project_name,
                "duration": (sim_data or {}).get("year_count"),
                "total_cost": fmt_money((sim_data or {}).get("total_cost_npv", 0)),
                "current_asset_value": fmt_money(start_val),
                "future_asset_value": fmt_money(end_val),
                "raw_start_asset_value": start_val,
                "raw_end_asset_value": end_val,
                "start_vci": start_vci,
                "end_vci": end_vci,
                "vci_change": round(end_vci - start_vci, 2),
            }

            # E) Generate
            ai_content = generate_strategic_narrative(context_payload)

            # F) Save to DB
            sql_insert = """
                INSERT INTO public.ai_insights
                    (project_id, simulation_run_id, content, status, created_by, insight_type, model, prompt_version)
                VALUES
                    (%s, %s, %s, 'final', %s, 'treasury_narrative', %s, %s)
                RETURNING
                    id, project_id, simulation_run_id, content, status, created_at, created_by, insight_type;
            """

            cur.execute(
                sql_insert,
                (
                    str(project_id),
                    str(active_run_id),
                    Json(ai_content),
                    user_id,
                    "gpt-4o",
                    "v1",
                ),
            )
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            conn.commit()

            record = dict(zip(cols, row))

            # Add simulation_summary for the frontend
            record["simulation_summary"] = {
                "run_name": run_name,
                "total_cost": context_payload["total_cost"],
                "end_vci": round(end_vci, 1),
            }

            return record


# -----------------------------------------------------------------------------
# 2. LIST HISTORY (The "Sublink" View)
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/advisor/history",
    response_model=List[AiInsightOut],
    summary="List past AI insights for this project.",
)
def list_ai_history(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(10, ge=1, le=50),
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Ownership check
            _assert_project_owned(cur, project_id, user_id)

            sql = """
                SELECT
                    ai.id, ai.project_id, ai.simulation_run_id,
                    ai.content, ai.status, ai.created_at, ai.created_by, ai.insight_type,
                    sr.run_name, sr.results_payload
                FROM public.ai_insights ai
                LEFT JOIN public.simulation_results sr
                    ON ai.simulation_run_id = sr.id
                WHERE ai.project_id = %s
                ORDER BY ai.created_at DESC
                LIMIT %s
            """
            cur.execute(sql, (str(project_id), limit))
            rows = cur.fetchall()

            results = []
            for row in rows:
                (
                    r_id, r_proj, r_sim_id,
                    r_content, r_status, r_created, r_by, r_type,
                    run_name, run_payload
                ) = row

                sim_summary = None
                if run_payload:
                    yearly = (run_payload or {}).get("yearly_data", [])
                    final_vci = float(yearly[-1].get("avg_condition_index", 0) or 0) if yearly else 0
                    cost = float((run_payload or {}).get("total_cost_npv", 0) or 0)

                    sim_summary = {
                        "run_name": run_name,
                        "total_cost": f"R {cost/1_000_000:.0f} M",
                        "end_vci": round(final_vci, 1),
                    }

                results.append(
                    {
                        "id": r_id,
                        "project_id": r_proj,
                        "simulation_run_id": r_sim_id,
                        "content": r_content,
                        "status": r_status,
                        "created_at": r_created,
                        "created_by": r_by,
                        "insight_type": r_type,
                        "simulation_summary": sim_summary,
                    }
                )

            return results