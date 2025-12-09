from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
import pandas as pd
from app.routers.projects import get_current_user_id, get_db_connection
from app.scenarios import service as scenario_service
from . import engine, schemas

router = APIRouter()

# --- 👇 THIS WAS MISSING: The Endpoint to fetch results ---
@router.get(
    "/{project_id}/simulation/latest",
    response_model=schemas.SimulationOutput,
    summary="Get results from the most recent simulation run"
)
def get_latest_simulation_result(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    # Fetch the Baseline Scenario ID first
    scenario = scenario_service.get_or_create_baseline(project_id, user_id)
    
    # Get the result specifically for this scenario
    sql = """
        SELECT results_payload
        FROM public.simulation_results
        WHERE project_id = %s AND scenario_id = %s
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), str(scenario.id)))
            row = cur.fetchone()
            
    if not row:
        raise HTTPException(404, "No simulation results found for this project.")
        
    return row[0]


# --- Existing Run Logic (Unchanged) ---
@router.post(
    "/{project_id}/simulation/run",
    response_model=schemas.SimulationOutput,
    summary="Trigger a RONET simulation run"
)
def run_simulation(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    # 1. Fetch Workbook Data (Segments + Lookups)
    try:
        sql = """
            SELECT workbook_payload 
            FROM public.master_data_uploads
            WHERE project_id = %s AND user_id = %s
            ORDER BY created_at DESC LIMIT 1;
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (str(project_id), user_id))
                row = cur.fetchone()
                
        if not row or not row[0]:
            raise HTTPException(404, "No master data found. Please upload a workbook first.")
            
        payload = row[0]
        
        if "segments" not in payload:
             raise HTTPException(400, "Workbook missing 'segments' sheet.")
        df_segments = pd.DataFrame(payload["segments"])
        
        # Extract Lookups
        df_costs = pd.DataFrame(payload.get("road_costs", []))
        df_iri = pd.DataFrame(payload.get("iri_defaults", []))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error loading master data: {e}")

    # 2. Fetch Scenario Parameters (The Sliders)
    # This fetches the 'analysis_duration' you saved in Step 2
    try:
        scenario = scenario_service.get_or_create_baseline(project_id, user_id)
    except Exception as e:
        raise HTTPException(500, f"Error loading scenario: {e}")

    # 3. Run Engine
    # The 'params' object contains the exact years set in your UI slider
    try:
        result = engine.run_ronet_simulation(
            project_id=project_id,
            scenario_id=scenario.id,
            segments_df=df_segments,
            costs_df=df_costs,
            iri_defaults_df=df_iri,
            params=scenario.parameters 
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Simulation engine failed: {e}")

    # 4. Save Results to DB (OVERWRITE MODE)
    # We delete any existing result for this specific scenario first
    sql_delete = """
        DELETE FROM public.simulation_results
        WHERE project_id = %s AND scenario_id = %s;
    """
    
    sql_insert = """
        INSERT INTO public.simulation_results 
        (project_id, scenario_id, results_payload, triggered_by)
        VALUES (%s, %s, %s, %s);
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Step A: Clear old run
            cur.execute(sql_delete, (str(project_id), str(scenario.id)))
            
            # Step B: Insert new run
            cur.execute(sql_insert, (
                str(project_id), 
                str(scenario.id), 
                result.model_dump_json(), 
                user_id
            ))
            conn.commit()

    return result