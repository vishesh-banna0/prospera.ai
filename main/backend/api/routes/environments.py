from __future__ import annotations

from dataclasses import replace
from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_simulator_service
from backend.modules.simulator.application.dto import (
    CreateEnvironmentInput,
    RenameEnvironmentInput,
)
from backend.modules.simulator.application.services import SimulatorService
from backend.shared.types import EnvironmentId

router = APIRouter(prefix="/environments", tags=["environments"])


@router.post("/")
async def create_environment(
    request: CreateEnvironmentInput,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Create a new simulator environment."""
    try:
        await service.create_environment(request)
        return {"status": "created", "message": "Environment created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{environment_id}")
async def rename_environment(
    environment_id: EnvironmentId,
    request: RenameEnvironmentInput,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Rename a simulator environment."""
    try:
        request = replace(request, environment_id=environment_id)
        await service.rename_environment(request)
        return {"status": "renamed", "environment_id": environment_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: EnvironmentId,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Delete a simulator environment."""
    try:
        await service.delete_environment(environment_id)
        return {"status": "deleted", "environment_id": environment_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


"""
Purpose:
Expose endpoints to create, rename, and delete simulator environments.

Responsibilities:
- Expose environment lifecycle endpoints
- Accept user or agent requests targeting isolated portfolio environments
- Delegate all behavior to simulator application services
- Handle HTTP error responses

Dependencies:
- backend.api.dependencies (get_simulator_service)
- backend.modules.simulator.application.commands
- backend.modules.simulator.application.dto

Endpoints:
- POST /environments: Create new environment
- PATCH /environments/{environment_id}: Rename environment
- DELETE /environments/{environment_id}: Delete environment

What Should Not Live Here:
- Persistence queries
- Pricing lookups from vendors
- Portfolio performance calculations
"""
