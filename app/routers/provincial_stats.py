from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
import pandas as pd
import io
from app.routers.projects import get_db_connection, get_current_user_id

router = APIRouter()

# --- SCHEMAS --------------------------------------------------------
class ProvincialStatUpdate(BaseModel):
    province_name: str
    km_arid: Optional[float] = 0
    km_semi_arid: Optional[float] = 0
    km_dry_sub_humid: Optional[float] = 0
    km_moist_sub_humid: Optional[float] = 0
    km_humid: Optional[float] = 0
    avg_vci: Optional[float] = 0
    vehicle_km: Optional[float] = 0
    fuel_sales: Optional[float] = 0

class ProvincialStatResponse(ProvincialStatUpdate):
    id: UUID
    project_id: UUID

# --- ENDPOINTS ------------------------------------------------------

@router.get("/{project_id}", response_model=List[ProvincialStatResponse])
def get_stats(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    """
    Returns the 9 rows. They are guaranteed to exist because of the SQL trigger.
    """
    sql = """
        SELECT * FROM public.provincial_stats
        WHERE project_id = %s
        ORDER BY province_name ASC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id),))
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]

@router.post("/{project_id}", status_code=200)
def save_manual_input(
    project_id: UUID, 
    stats: List[ProvincialStatUpdate], 
    user_id: str = Depends(get_current_user_id)
):
    """
    Saves user edits from the grid.
    Uses 'UPDATE' because the rows already exist.
    """
    sql = """
        UPDATE public.provincial_stats
        SET 
            km_arid = %s, km_semi_arid = %s, km_dry_sub_humid = %s, 
            km_moist_sub_humid = %s, km_humid = %s,
            avg_vci = %s, vehicle_km = %s, fuel_sales = %s,
            updated_at = NOW()
        WHERE project_id = %s AND province_name = %s;
    """
    
    values = []
    for s in stats:
        values.append((
            s.km_arid, s.km_semi_arid, s.km_dry_sub_humid, 
            s.km_moist_sub_humid, s.km_humid,
            s.avg_vci, s.vehicle_km, s.fuel_sales,
            str(project_id), s.province_name
        ))

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Execute batch update
            cur.executemany(sql, values)
            conn.commit()
            
    return {"message": "Saved successfully"}

@router.post("/{project_id}/upload")
def upload_stats_csv(
    project_id: UUID, 
    file: UploadFile = File(...), 
    user_id: str = Depends(get_current_user_id)
):
    """
    Parses 'Book1.csv' and updates the existing 9 rows.
    """
    try:
        contents = file.file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), header=None)
        else:
            df = pd.read_excel(io.BytesIO(contents), header=None)

        # Basic Cleanup tailored to your CSV structure
        df = df.iloc[3:] # Skip headers
        df = df[df[0].notna()] # Remove empty lines
        
        updates = []
        for _, row in df.iterrows():
            prov_name = str(row[0]).strip()
            # Skip totals/junk
            if "Total" in prov_name or "Province" in prov_name:
                continue

            def parse(val):
                if isinstance(val, (int, float)): return val
                if isinstance(val, str):
                    clean = val.replace('R','').replace(',','').replace(' ','').replace('%','')
                    try: return float(clean)
                    except: return 0
                return 0

            # Map CSV Columns to DB Columns
            updates.append((
                parse(row[1]), parse(row[2]), parse(row[3]), parse(row[4]), parse(row[5]), # Climate Kms
                parse(row[7]), parse(row[8]), parse(row[10]), # VCI, VehKm, Fuel
                str(project_id), prov_name # WHERE clause
            ))

        sql = """
            UPDATE public.provincial_stats
            SET 
                km_arid=%s, km_semi_arid=%s, km_dry_sub_humid=%s, km_moist_sub_humid=%s, km_humid=%s,
                avg_vci=%s, vehicle_km=%s, fuel_sales=%s, updated_at=NOW()
            WHERE project_id=%s AND province_name=%s;
        """

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, updates)
                conn.commit()

        return {"message": "Spreadsheet data imported"}

    except Exception as e:
        raise HTTPException(400, f"Upload Error: {str(e)}")