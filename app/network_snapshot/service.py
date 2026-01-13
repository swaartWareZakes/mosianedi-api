from uuid import UUID
from typing import Optional, Dict, Any

from fastapi import HTTPException
from app.routers.projects import get_db_connection


def _fetch_project(project_id: UUID, user_id: str) -> Dict[str, Any]:
    sql = """
        SELECT
          id,
          user_id,
          project_name,
          province,
          start_year,
          proposal_title,
          proposal_status,
          created_at,
          updated_at
        FROM public.projects
        WHERE id = %s AND user_id = %s
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))


def _fetch_proposal_data(project_id: UUID, user_id: str) -> Dict[str, Any]:
    sql = """
        SELECT
          id,
          project_id,
          user_id,
          data_source,

          paved_arid,
          paved_semi_arid,
          paved_dry_sub_humid,
          paved_moist_sub_humid,
          paved_humid,

          gravel_arid,
          gravel_semi_arid,
          gravel_dry_sub_humid,
          gravel_moist_sub_humid,
          gravel_humid,

          avg_vci_used,
          vehicle_km,
          pct_vehicle_km_used,
          fuel_sales,
          pct_fuel_sales_used,
          fuel_option_selected,
          target_vci,

          extra_inputs,
          created_at,
          updated_at
        FROM public.proposal_data
        WHERE project_id = %s AND user_id = %s
        LIMIT 1;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Proposal data not found for this project. (Expected row from Option A)",
                )
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))


def _n(x: Optional[float]) -> float:
    return float(x or 0)


def get_network_snapshot(project_id: UUID, user_id: str) -> Dict[str, Any]:
    project = _fetch_project(project_id, user_id)
    proposal = _fetch_proposal_data(project_id, user_id)

    paved_total = (
        _n(proposal.get("paved_arid"))
        + _n(proposal.get("paved_semi_arid"))
        + _n(proposal.get("paved_dry_sub_humid"))
        + _n(proposal.get("paved_moist_sub_humid"))
        + _n(proposal.get("paved_humid"))
    )

    gravel_total = (
        _n(proposal.get("gravel_arid"))
        + _n(proposal.get("gravel_semi_arid"))
        + _n(proposal.get("gravel_dry_sub_humid"))
        + _n(proposal.get("gravel_moist_sub_humid"))
        + _n(proposal.get("gravel_humid"))
    )

    network_total = paved_total + gravel_total

    climate_breakdown = {
        "paved": {
            "arid": _n(proposal.get("paved_arid")),
            "semi_arid": _n(proposal.get("paved_semi_arid")),
            "dry_sub_humid": _n(proposal.get("paved_dry_sub_humid")),
            "moist_sub_humid": _n(proposal.get("paved_moist_sub_humid")),
            "humid": _n(proposal.get("paved_humid")),
            "total": paved_total,
        },
        "gravel": {
            "arid": _n(proposal.get("gravel_arid")),
            "semi_arid": _n(proposal.get("gravel_semi_arid")),
            "dry_sub_humid": _n(proposal.get("gravel_dry_sub_humid")),
            "moist_sub_humid": _n(proposal.get("gravel_moist_sub_humid")),
            "humid": _n(proposal.get("gravel_humid")),
            "total": gravel_total,
        },
        "network_total": network_total,
    }

    indicators = {
        "avg_vci_used": _n(proposal.get("avg_vci_used")),
        "vehicle_km": _n(proposal.get("vehicle_km")),
        "pct_vehicle_km_used": _n(proposal.get("pct_vehicle_km_used")),
        "fuel_sales": _n(proposal.get("fuel_sales")),
        "pct_fuel_sales_used": _n(proposal.get("pct_fuel_sales_used")),
        "fuel_option_selected": int(proposal.get("fuel_option_selected") or 1),
        "target_vci": _n(proposal.get("target_vci")),
        "extra_inputs": proposal.get("extra_inputs") or {},
    }

    return {
        "project": {
            "id": str(project.get("id")),
            "project_name": project.get("project_name"),
            "province": project.get("province"),
            "start_year": project.get("start_year"),
            "proposal_title": project.get("proposal_title"),
            "proposal_status": project.get("proposal_status"),
        },
        "snapshot": {
            "status": "ok",
            "message": "Snapshot derived from proposal_data (new flow).",
            "climate_breakdown": climate_breakdown,
            "indicators": indicators,
        },
    }