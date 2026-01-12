from typing import Dict, Any, List, Tuple
from .schemas import ProposalDataPayload
from .service import compute_paved_total, compute_gravel_total

class ProposalValidationError(Exception):
    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__("Proposal data validation failed")
        self.errors = errors

def validate_proposal_data(payload: ProposalDataPayload) -> Tuple[bool, List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    total = compute_paved_total(payload) + compute_gravel_total(payload)

    if total <= 0:
        errors.append({"field": "total_lane_km", "message": "Total network length must be > 0.", "code": "TOTAL_LANE_KM_ZERO"})

    if payload.avg_vci_used <= 0:
        errors.append({"field": "avg_vci_used", "message": "Average VCI must be > 0.", "code": "AVG_VCI_REQUIRED"})

    if payload.vehicle_km <= 0:
        errors.append({"field": "vehicle_km", "message": "Vehicle-km must be > 0.", "code": "VEHICLE_KM_REQUIRED"})

    if payload.fuel_sales <= 0:
        errors.append({"field": "fuel_sales", "message": "Fuel sales must be > 0.", "code": "FUEL_SALES_REQUIRED"})

    if payload.fuel_option_selected not in (1, 2):
        errors.append({"field": "fuel_option_selected", "message": "Fuel option must be 1 or 2.", "code": "INVALID_FUEL_OPTION"})

    return (len(errors) == 0), errors

def validate_or_raise(payload: ProposalDataPayload) -> None:
    ok, errors = validate_proposal_data(payload)
    if not ok:
        raise ProposalValidationError(errors)
