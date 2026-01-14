from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
import json
from app.routers.projects import get_current_user_id, get_db_connection
from .service import generate_strategic_narrative

router = APIRouter()

@router.get(
    "/{project_id}/advisor/generate",
    summary="Generate AI Strategic Feedback based on latest simulation"
)
def get_ai_feedback(
    project_id: UUID,
    user_id: str = Depends(get_current_user_id)
):
    # 1. Fetch Project Meta (Name)
    project_name = "Unknown Project"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT project_name FROM projects WHERE id = %s", (str(project_id),))
            row = cur.fetchone()
            if row:
                project_name = row[0]

            # 2. Fetch Latest Simulation Result
            cur.execute("""
                SELECT results_payload 
                FROM simulation_results 
                WHERE project_id = %s 
                ORDER BY run_at DESC LIMIT 1
            """, (str(project_id),))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(404, "No simulation data found. Run a simulation first.")
                
            sim_data = row[0] # This is the JSON dict from the DB

    # 3. Simplify Data for the AI (Don't send huge arrays)
    # We extract only what matters for the story
    yearly = sim_data.get("yearly_data", [])
    if not yearly:
        raise HTTPException(400, "Corrupt simulation data.")

    start_vci = yearly[0].get("avg_condition_index")
    end_vci = yearly[-1].get("avg_condition_index")
    
    # Format huge numbers to readable strings (e.g., "R 40.5 Billion")
    def fmt_money(x):
        return f"R {x/1_000_000_000:.2f} Billion" if x > 1_000_000_000 else f"R {x/1_000_000:.1f} Million"

    context_payload = {
        "project_name": project_name,
        "duration": sim_data.get("year_count"),
        "current_asset_value": fmt_money(yearly[0].get("asset_value", 0)),
        "start_vci": start_vci,
        "end_vci": end_vci,
        "vci_change": round(end_vci - start_vci, 2),
        "total_cost": fmt_money(sim_data.get("total_cost_npv", 0)),
        "inflation": 6.0 # Hardcoded or fetch from forecast params if you prefer
    }

    # 4. Call the AI Brain
    ai_response = generate_strategic_narrative(context_payload)
    
    return ai_response