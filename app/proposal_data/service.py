from .schemas import ProposalDataPayload

def compute_paved_total(p: ProposalDataPayload) -> float:
    return p.paved_arid + p.paved_semi_arid + p.paved_dry_sub_humid + p.paved_moist_sub_humid + p.paved_humid

def compute_gravel_total(p: ProposalDataPayload) -> float:
    return p.gravel_arid + p.gravel_semi_arid + p.gravel_dry_sub_humid + p.gravel_moist_sub_humid + p.gravel_humid
