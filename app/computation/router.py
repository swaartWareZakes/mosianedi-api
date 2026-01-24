from __future__ import annotations

from uuid import UUID
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import Json

from app.routers.projects import get_current_user_id, get_db_connection
from app.scenarios import service as scenario_service
from . import engine, schemas

router = APIRouter()


# -----------------------------------------------------------------------------
# Helper: verify project belongs to user (security + demo safety)
# -----------------------------------------------------------------------------
def _assert_project_owned(project_id: UUID, user_id: str) -> None:
    sql = "SELECT 1 FROM public.projects WHERE id = %s AND user_id = %s"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Project not found.")


# -----------------------------------------------------------------------------
# 1. RUN SIMULATION (Saves History + Snapshots) + set ACTIVE
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/simulation/run",
    response_model=schemas.SimulationRunOut,
    summary="Run simulation, save snapshot, and set as ACTIVE.",
)
def run_simulation(
    project_id: UUID,
    options: schemas.SimulationRunOptions,
    user_id: str = Depends(get_current_user_id),
):
    _assert_project_owned(project_id, user_id)

    # 1) Load prerequisites
    try:
        scenario_params = scenario_service.get_forecast(project_id, user_id)
        from app.network_snapshot.service import get_network_snapshot
        network_profile = get_network_snapshot(project_id, user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading prerequisites: {e}")

    # 2) Run engine
    try:
        result = engine.run_ronet_simulation(
            project_id=project_id,
            params=scenario_params,
            network_profile=network_profile,
            options=options,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation engine failed: {e}")

    # 3) JSON-safe snapshots (IMPORTANT)
    assumptions_dict = scenario_params.model_dump(mode="json")
    run_options_dict = options.model_dump(mode="json", by_alias=True)
    results_dict = result.model_dump(mode="json")

    scenario_id = str(getattr(scenario_params, "id", None)) if getattr(scenario_params, "id", None) else None
    final_run_name = options.run_name or f"Run {result.generated_at.strftime('%H:%M')}"

    sql_insert = """
        INSERT INTO public.simulation_results
            (project_id, scenario_id, results_payload, triggered_by, status,
             run_name, run_options, assumptions_snapshot, network_snapshot, notes)
        VALUES
            (%s, %s, %s, %s, 'completed',
             %s, %s, %s, %s, %s)
        RETURNING
            id, project_id, scenario_id, results_payload, run_at, triggered_by, status,
            run_name, run_options, assumptions_snapshot, network_snapshot, notes;
    """

    sql_update_project = """
        UPDATE public.projects
        SET active_simulation_run_id = %s, updated_at = NOW()
        WHERE id = %s AND user_id = %s;
    """

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                # A) Insert the Simulation Result
                cur.execute(
                    sql_insert,
                    (
                        str(project_id),
                        scenario_id,
                        Json(results_dict),
                        user_id,  # sub from Supabase is a UUID string, OK for PG uuid
                        final_run_name,
                        Json(run_options_dict),
                        Json(assumptions_dict),
                        Json(network_profile),
                        options.notes,
                    ),
                )
                new_run_row = cur.fetchone()
                cols = [d[0] for d in cur.description]  # ✅ capture NOW (before UPDATE)
                new_run_id = new_run_row[0]

                # B) Set active run (ownership safe)
                cur.execute(sql_update_project, (str(new_run_id), str(project_id), user_id))

            conn.commit()
            return dict(zip(cols, new_run_row))

        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save simulation result: {e}")


# -----------------------------------------------------------------------------
# 2. GET ACTIVE SIMULATION (proposal baseline)
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/simulation/latest",
    response_model=schemas.SimulationRunOut,
    summary="Get the ACTIVE simulation run (or most recent if none active)",
)
def get_latest_simulation(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    _assert_project_owned(project_id, user_id)

    sql_check_active = """
        SELECT active_simulation_run_id
        FROM public.projects
        WHERE id = %s AND user_id = %s
    """

    sql_fetch_run = """
        SELECT
            id, project_id, scenario_id, results_payload, run_at, triggered_by, status,
            run_name, run_options, assumptions_snapshot, network_snapshot, notes
        FROM public.simulation_results
        WHERE id = %s AND project_id = %s
    """

    sql_fallback = """
        SELECT
            id, project_id, scenario_id, results_payload, run_at, triggered_by, status,
            run_name, run_options, assumptions_snapshot, network_snapshot, notes
        FROM public.simulation_results
        WHERE project_id = %s
        ORDER BY run_at DESC
        LIMIT 1
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_check_active, (str(project_id), user_id))
            proj_row = cur.fetchone()
            active_id = proj_row[0] if proj_row else None

            target_row = None

            if active_id:
                cur.execute(sql_fetch_run, (str(active_id), str(project_id)))
                target_row = cur.fetchone()

            if not target_row:
                cur.execute(sql_fallback, (str(project_id),))
                target_row = cur.fetchone()

            if not target_row:
                raise HTTPException(status_code=404, detail="No simulation results found.")

            cols = [d[0] for d in cur.description]
            return dict(zip(cols, target_row))


# -----------------------------------------------------------------------------
# 3. LIST HISTORY
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/simulation/history",
    response_model=List[schemas.SimulationRunOut],
    summary="List all past simulation runs",
)
def list_simulation_history(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
):
    _assert_project_owned(project_id, user_id)

    sql = """
        SELECT
            id, project_id, scenario_id, results_payload, run_at, triggered_by, status,
            run_name, run_options, assumptions_snapshot, network_snapshot, notes
        FROM public.simulation_results
        WHERE project_id = %s
        ORDER BY run_at DESC
        LIMIT %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), limit))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]


# -----------------------------------------------------------------------------
# 4. SET ACTIVE RUN
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/simulation/active/{run_id}",
    status_code=200,
    summary="Switch active proposal baseline to a specific past run.",
)
def set_active_simulation(
    project_id: UUID,
    run_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    _assert_project_owned(project_id, user_id)

    sql_verify = "SELECT 1 FROM public.simulation_results WHERE id = %s AND project_id = %s"

    sql_update = """
        UPDATE public.projects
        SET active_simulation_run_id = %s, updated_at = NOW()
        WHERE id = %s AND user_id = %s
    """

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql_verify, (str(run_id), str(project_id)))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Simulation run not found in this project.")

                cur.execute(sql_update, (str(run_id), str(project_id), user_id))
            conn.commit()
            return {"message": "Active simulation updated", "active_run_id": str(run_id)}
        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error switching active run: {e}")