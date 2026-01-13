from uuid import UUID
from typing import Dict, Any
from app.routers.projects import get_db_connection

def _n(x) -> float:
    """Helper to convert None to 0.0"""
    return float(x or 0)

def get_network_snapshot(project_id: UUID, user_id: str) -> Dict[str, Any]:
    # 1. Fetch Proposal Inputs
    sql = """
        SELECT 
            paved_arid, paved_semi_arid, paved_dry_sub_humid, paved_moist_sub_humid, paved_humid,
            gravel_arid, gravel_semi_arid, gravel_dry_sub_humid, gravel_moist_sub_humid, gravel_humid,
            avg_vci_used, vehicle_km, fuel_sales
        FROM public.proposal_data
        WHERE project_id = %s AND user_id = %s
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            
            # If no data found, return zeros
            if not row:
                return {
                    "totalLengthKm": 0, "pavedLengthKm": 0, "gravelLengthKm": 0,
                    "avgVci": 0, "assetValue": 0, "totalVehicleKm": 0, "fuelSales": 0
                }
                
            data = dict(zip([d[0] for d in cur.description], row))

    # 2. Sum up lengths
    paved_total = (
        _n(data.get("paved_arid")) + _n(data.get("paved_semi_arid")) + 
        _n(data.get("paved_dry_sub_humid")) + _n(data.get("paved_moist_sub_humid")) + _n(data.get("paved_humid"))
    )
    
    gravel_total = (
        _n(data.get("gravel_arid")) + _n(data.get("gravel_semi_arid")) + 
        _n(data.get("gravel_dry_sub_humid")) + _n(data.get("gravel_moist_sub_humid")) + _n(data.get("gravel_humid"))
    )
    
    total_km = paved_total + gravel_total

    # 3. Calculate Asset Value (CRC)
    # Using standard engineering estimates (adjust as needed)
    RATE_PAVED = 3_500_000   # R3.5m per km
    RATE_GRAVEL = 250_000    # R250k per km
    
    asset_value = (paved_total * RATE_PAVED) + (gravel_total * RATE_GRAVEL)

    # 4. Return Flat Structure (matching React state)
    return {
        "totalLengthKm": round(total_km, 2),
        "pavedLengthKm": round(paved_total, 2),
        "gravelLengthKm": round(gravel_total, 2),
        "avgVci": _n(data.get("avg_vci_used")),
        "assetValue": round(asset_value, 2),
        "totalVehicleKm": _n(data.get("vehicle_km")),
        "fuelSales": _n(data.get("fuel_sales"))
    }