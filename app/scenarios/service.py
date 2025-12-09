# app/scenarios/service.py

from uuid import UUID
from typing import List

from fastapi import HTTPException

from .schemas import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioRead,
    ScenarioSummary,
)
from . import repository as repo


def create_scenario(
    project_id: UUID,
    user_id: str,
    payload: ScenarioCreate,
) -> ScenarioRead:
    data = repo.create_scenario(project_id, user_id, payload.dict())
    return ScenarioRead(**data)


def list_scenarios(
    project_id: UUID,
    user_id: str,
) -> List[ScenarioSummary]:
    rows = repo.list_scenarios(project_id, user_id)
    return [
        ScenarioSummary(
            id=row["id"],
            name=row["name"],
            is_baseline=row["is_baseline"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str,
) -> ScenarioRead:
    row = repo.get_scenario(project_id, scenario_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return ScenarioRead(**row)


def update_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str,
    payload: ScenarioUpdate,
) -> ScenarioRead:
    row = repo.update_scenario(project_id, scenario_id, user_id, payload.dict(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return ScenarioRead(**row)


def delete_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user_id: str,
) -> None:
    ok = repo.delete_scenario(project_id, scenario_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Scenario not found.")