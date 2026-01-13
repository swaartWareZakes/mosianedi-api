from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.routers.projects import get_current_user_id
from app.scenarios import service as scenario_service
from . import engine, schemas

router = APIRouter()

@router.post(
    "/{project_id}/simulation/run",
    response_model=schemas.SimulationOutput,
    summary="Trigger a Simulation based on Forecast Parameters"
)
def run_simulation(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    # 1. Fetch Forecast Parameters (The new Scenario)
    try:
        scenario_params = scenario_service.get_forecast(project_id, user_id)
    except Exception as e:
        raise HTTPException(500, f"Error loading forecast parameters: {e}")

    # 2. Run Engine (Now using the new simplified engine)
    try:
        result = engine.run_ronet_simulation(
            project_id=project_id,
            params=scenario_params
        )
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Simulation engine failed: {e}")