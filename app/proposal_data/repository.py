from typing import Optional, Dict, Any
from datetime import datetime

def assert_project_owned(conn, project_id: str, user_id: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM public.projects WHERE id = %s AND user_id = %s",
        (project_id, user_id),
    )
    ok = cur.fetchone()
    cur.close()
    if not ok:
        raise ValueError("Project not found or not owned by user")

def get_proposal_data(conn, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    # ownership check
    assert_project_owned(conn, project_id, user_id)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          paved_arid, paved_semi_arid, paved_dry_sub_humid, paved_moist_sub_humid, paved_humid,
          gravel_arid, gravel_semi_arid, gravel_dry_sub_humid, gravel_moist_sub_humid, gravel_humid,
          avg_vci_used, vehicle_km, pct_vehicle_km_used,
          fuel_sales, pct_fuel_sales_used, fuel_option_selected, target_vci,
          extra_inputs, updated_at
        FROM public.proposal_data
        WHERE project_id = %s AND user_id = %s
        """,
        (project_id, user_id),
    )
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    cur.close()

    if not row:
        return None

    data = dict(zip(cols, row))
    updated_at = data.get("updated_at")
    if isinstance(updated_at, datetime):
        data["updated_at"] = updated_at.isoformat()

    return data

def upsert_proposal_data(conn, project_id: str, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    assert_project_owned(conn, project_id, user_id)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO public.proposal_data (
          project_id, user_id, data_source,
          paved_arid, paved_semi_arid, paved_dry_sub_humid, paved_moist_sub_humid, paved_humid,
          gravel_arid, gravel_semi_arid, gravel_dry_sub_humid, gravel_moist_sub_humid, gravel_humid,
          avg_vci_used, vehicle_km, pct_vehicle_km_used,
          fuel_sales, pct_fuel_sales_used, fuel_option_selected, target_vci,
          extra_inputs, updated_at
        )
        VALUES (
          %s, %s, 'manual',
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s,
          %s, %s, %s,
          %s, %s, %s, %s,
          %s, now()
        )
        ON CONFLICT (project_id)
        DO UPDATE SET
          user_id = EXCLUDED.user_id,
          data_source = EXCLUDED.data_source,

          paved_arid = EXCLUDED.paved_arid,
          paved_semi_arid = EXCLUDED.paved_semi_arid,
          paved_dry_sub_humid = EXCLUDED.paved_dry_sub_humid,
          paved_moist_sub_humid = EXCLUDED.paved_moist_sub_humid,
          paved_humid = EXCLUDED.paved_humid,

          gravel_arid = EXCLUDED.gravel_arid,
          gravel_semi_arid = EXCLUDED.gravel_semi_arid,
          gravel_dry_sub_humid = EXCLUDED.gravel_dry_sub_humid,
          gravel_moist_sub_humid = EXCLUDED.gravel_moist_sub_humid,
          gravel_humid = EXCLUDED.gravel_humid,

          avg_vci_used = EXCLUDED.avg_vci_used,
          vehicle_km = EXCLUDED.vehicle_km,
          pct_vehicle_km_used = EXCLUDED.pct_vehicle_km_used,

          fuel_sales = EXCLUDED.fuel_sales,
          pct_fuel_sales_used = EXCLUDED.pct_fuel_sales_used,
          fuel_option_selected = EXCLUDED.fuel_option_selected,
          target_vci = EXCLUDED.target_vci,

          extra_inputs = EXCLUDED.extra_inputs,
          updated_at = now()
        RETURNING
          paved_arid, paved_semi_arid, paved_dry_sub_humid, paved_moist_sub_humid, paved_humid,
          gravel_arid, gravel_semi_arid, gravel_dry_sub_humid, gravel_moist_sub_humid, gravel_humid,
          avg_vci_used, vehicle_km, pct_vehicle_km_used,
          fuel_sales, pct_fuel_sales_used, fuel_option_selected, target_vci,
          extra_inputs, updated_at
        """,
        (
            project_id, user_id,
            payload["paved_arid"], payload["paved_semi_arid"], payload["paved_dry_sub_humid"], payload["paved_moist_sub_humid"], payload["paved_humid"],
            payload["gravel_arid"], payload["gravel_semi_arid"], payload["gravel_dry_sub_humid"], payload["gravel_moist_sub_humid"], payload["gravel_humid"],
            payload["avg_vci_used"], payload["vehicle_km"], payload["pct_vehicle_km_used"],
            payload["fuel_sales"], payload["pct_fuel_sales_used"], payload["fuel_option_selected"], payload["target_vci"],
            payload["extra_inputs"],
        ),
    )

    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    conn.commit()
    cur.close()

    data = dict(zip(cols, row))
    updated_at = data.get("updated_at")
    if isinstance(updated_at, datetime):
        data["updated_at"] = updated_at.isoformat()

    return data
