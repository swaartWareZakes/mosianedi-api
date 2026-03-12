from uuid import UUID
from typing import Dict, Any
from app.dependencies import get_db_connection

def _n(x) -> float:
    """Helper to convert None to 0.0"""
    return float(x or 0)

def get_network_snapshot(project_id: UUID, user_id: str) -> Dict[str, Any]:
    # 1. Fetch Project Scope AND Proposal Inputs together
    sql = """
        SELECT 
            p.scope, p.route_length_km, p.surface_type, p.route_specific_vci, p.route_daily_traffic,
            pd.paved_arid, pd.paved_semi_arid, pd.paved_dry_sub_humid, pd.paved_moist_sub_humid, pd.paved_humid,
            pd.gravel_arid, pd.gravel_semi_arid, pd.gravel_dry_sub_humid, pd.gravel_moist_sub_humid, pd.gravel_humid,
            pd.avg_vci_used, pd.vehicle_km, pd.fuel_sales
        FROM public.projects p
        LEFT JOIN public.proposal_data pd ON p.id = pd.project_id
        WHERE p.id = %s AND p.user_id = %s
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            
            if not row:
                return {
                    "totalLengthKm": 0, "pavedLengthKm": 0, "gravelLengthKm": 0,
                    "avgVci": 0, "assetValue": 0, "totalVehicleKm": 0, "fuelSales": 0
                }
                
            data = dict(zip([d[0] for d in cur.description], row))

    scope = data.get("scope")

    # ==========================================
    # ROUTE SCOPE LOGIC (Linear Asset)
    # ==========================================
    if scope == 'route':
        length = _n(data.get("route_length_km"))
        is_paved = data.get("surface_type") == 'paved'
        
        paved_total = length if is_paved else 0.0
        gravel_total = length if not is_paved else 0.0
        total_km = length
        
        vci = _n(data.get("route_specific_vci"))
        traffic = _n(data.get("route_daily_traffic"))
        fuel = 0.0 # Not typically tracked for a single route
        
    # ==========================================
    # NETWORK SCOPE LOGIC (Provincial/Municipal/Local)
    # ==========================================
    else:
        paved_total = (
            _n(data.get("paved_arid")) + _n(data.get("paved_semi_arid")) + 
            _n(data.get("paved_dry_sub_humid")) + _n(data.get("paved_moist_sub_humid")) + _n(data.get("paved_humid"))
        )
        
        gravel_total = (
            _n(data.get("gravel_arid")) + _n(data.get("gravel_semi_arid")) + 
            _n(data.get("gravel_dry_sub_humid")) + _n(data.get("gravel_moist_sub_humid")) + _n(data.get("gravel_humid"))
        )
        
        total_km = paved_total + gravel_total
        vci = _n(data.get("avg_vci_used"))
        traffic = _n(data.get("vehicle_km"))
        fuel = _n(data.get("fuel_sales"))

    # 3. Calculate Asset Value (CRC)
    RATE_PAVED = 3_500_000   # R3.5m per km
    RATE_GRAVEL = 250_000    # R250k per km
    
    asset_value = (paved_total * RATE_PAVED) + (gravel_total * RATE_GRAVEL)

    # 4. Return Standardized Flat Structure
    # (The simulation engine consumes this blindly, ensuring perfect compatibility!)
    return {
        "totalLengthKm": round(total_km, 2),
        "pavedLengthKm": round(paved_total, 2),
        "gravelLengthKm": round(gravel_total, 2),
        "avgVci": vci,
        "assetValue": round(asset_value, 2),
        "totalVehicleKm": traffic,
        "fuelSales": fuel
    }