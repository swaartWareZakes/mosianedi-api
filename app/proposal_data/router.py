from fastapi import APIRouter, Depends, HTTPException
from app.routers.projects import get_db_connection, get_current_user_id

from .schemas import ProposalDataPayload, ProposalDataResponse
from .validation import validate_or_raise, ProposalValidationError
from .service import compute_paved_total, compute_gravel_total
from . import repository

router = APIRouter()

@router.get("/{project_id}/proposal-data", response_model=ProposalDataResponse)
def read_proposal_data(project_id: str, user_id: str = Depends(get_current_user_id)):
    with get_db_connection() as conn:
        row = repository.get_proposal_data(conn, project_id, user_id)

        # If not created yet, return empty defaults (UI can show empty form)
        if row is None:
            payload = ProposalDataPayload()
            paved_total = compute_paved_total(payload)
            gravel_total = compute_gravel_total(payload)
            return ProposalDataResponse(
                project_id=project_id,
                user_id=user_id,
                paved_total_lane_km=paved_total,
                gravel_total_lane_km=gravel_total,
                total_lane_km=paved_total + gravel_total,
                payload=payload,
                updated_at=None,
            )

        payload = ProposalDataPayload(
            paved_arid=float(row["paved_arid"] or 0),
            paved_semi_arid=float(row["paved_semi_arid"] or 0),
            paved_dry_sub_humid=float(row["paved_dry_sub_humid"] or 0),
            paved_moist_sub_humid=float(row["paved_moist_sub_humid"] or 0),
            paved_humid=float(row["paved_humid"] or 0),
            gravel_arid=float(row["gravel_arid"] or 0),
            gravel_semi_arid=float(row["gravel_semi_arid"] or 0),
            gravel_dry_sub_humid=float(row["gravel_dry_sub_humid"] or 0),
            gravel_moist_sub_humid=float(row["gravel_moist_sub_humid"] or 0),
            gravel_humid=float(row["gravel_humid"] or 0),
            avg_vci_used=float(row["avg_vci_used"] or 0),
            vehicle_km=float(row["vehicle_km"] or 0),
            pct_vehicle_km_used=float(row["pct_vehicle_km_used"] or 0),
            fuel_sales=float(row["fuel_sales"] or 0),
            pct_fuel_sales_used=float(row["pct_fuel_sales_used"] or 0),
            fuel_option_selected=int(row["fuel_option_selected"] or 1),
            target_vci=float(row["target_vci"] or 45),
            extra_inputs=row.get("extra_inputs") or {},
        )

        paved_total = compute_paved_total(payload)
        gravel_total = compute_gravel_total(payload)

        return ProposalDataResponse(
            project_id=project_id,
            user_id=user_id,
            paved_total_lane_km=paved_total,
            gravel_total_lane_km=gravel_total,
            total_lane_km=paved_total + gravel_total,
            payload=payload,
            updated_at=row.get("updated_at"),
        )

@router.put("/{project_id}/proposal-data", response_model=ProposalDataResponse)
def save_proposal_data(project_id: str, body: ProposalDataPayload, user_id: str = Depends(get_current_user_id)):
    try:
        validate_or_raise(body)
    except ProposalValidationError as e:
        raise HTTPException(status_code=422, detail={"errors": e.errors})

    payload_dict = body.model_dump()

    with get_db_connection() as conn:
        saved = repository.upsert_proposal_data(conn, project_id, user_id, payload_dict)

        # rebuild payload from saved row
        payload = ProposalDataPayload(
            paved_arid=float(saved["paved_arid"] or 0),
            paved_semi_arid=float(saved["paved_semi_arid"] or 0),
            paved_dry_sub_humid=float(saved["paved_dry_sub_humid"] or 0),
            paved_moist_sub_humid=float(saved["paved_moist_sub_humid"] or 0),
            paved_humid=float(saved["paved_humid"] or 0),
            gravel_arid=float(saved["gravel_arid"] or 0),
            gravel_semi_arid=float(saved["gravel_semi_arid"] or 0),
            gravel_dry_sub_humid=float(saved["gravel_dry_sub_humid"] or 0),
            gravel_moist_sub_humid=float(saved["gravel_moist_sub_humid"] or 0),
            gravel_humid=float(saved["gravel_humid"] or 0),
            avg_vci_used=float(saved["avg_vci_used"] or 0),
            vehicle_km=float(saved["vehicle_km"] or 0),
            pct_vehicle_km_used=float(saved["pct_vehicle_km_used"] or 0),
            fuel_sales=float(saved["fuel_sales"] or 0),
            pct_fuel_sales_used=float(saved["pct_fuel_sales_used"] or 0),
            fuel_option_selected=int(saved["fuel_option_selected"] or 1),
            target_vci=float(saved["target_vci"] or 45),
            extra_inputs=saved.get("extra_inputs") or {},
        )

        paved_total = compute_paved_total(payload)
        gravel_total = compute_gravel_total(payload)

        return ProposalDataResponse(
            project_id=project_id,
            user_id=user_id,
            paved_total_lane_km=paved_total,
            gravel_total_lane_km=gravel_total,
            total_lane_km=paved_total + gravel_total,
            payload=payload,
            updated_at=saved.get("updated_at"),
        )
