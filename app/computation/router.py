from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
import json
from app.routers.projects import get_current_user_id, get_db_connection
from app.scenarios import service as scenario_service
from . import engine, schemas

router = APIRouter()

@router.post(
    "/{project_id}/simulation/run",
    response_model=schemas.SimulationOutput,
    summary="Trigger a Simulation and SAVE results"
)
def run_simulation(
    project_id: UUID,
    options: schemas.SimulationRunOptions,
    user_id: str = Depends(get_current_user_id)
):
    # 1. Load Prerequisites
    try:
        scenario_params = scenario_service.get_forecast(project_id, user_id)
        from app.network_snapshot.service import get_network_snapshot
        network_profile = get_network_snapshot(project_id, user_id)
    except Exception as e:
        raise HTTPException(500, f"Error loading prerequisites: {e}")

    # 2. Run Engine
    try:
        result = engine.run_ronet_simulation(
            project_id=project_id,
            params=scenario_params,
            network_profile=network_profile,
            options=options
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Simulation engine failed: {e}")

    # 3. SAVE to Database (The Missing Piece)
    # We overwrite the previous result for this project/scenario
    sql_delete = "DELETE FROM public.simulation_results WHERE project_id = %s"
    
    sql_insert = """
        INSERT INTO public.simulation_results 
        (project_id, scenario_id, results_payload, triggered_by)
        VALUES (%s, %s, %s, %s)
    """
    
    # We use a dummy scenario ID since we flattened the scenario table
    # or use the forecast ID if you want to be strict.
    dummy_scenario_id = scenario_params.id 

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Clear old run
            cur.execute(sql_delete, (str(project_id),))
            
            # Save new run
            cur.execute(sql_insert, (
                str(project_id), 
                str(dummy_scenario_id), 
                result.model_dump_json(), 
                user_id
            ))
            conn.commit()

    return result

# --- NEW: Endpoint for the Dashboard to READ the result ---
@router.get(
    "/{project_id}/simulation/latest",
    response_model=schemas.SimulationOutput,
    summary="Get the most recent simulation result"
)
def get_latest_simulation(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    sql = """
        SELECT results_payload 
        FROM public.simulation_results 
        WHERE project_id = %s 
        ORDER BY run_at DESC 
        LIMIT 1
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id),))
            row = cur.fetchone()
            
    if not row:
        raise HTTPException(404, "No simulation results found.")
        
    return row[0]