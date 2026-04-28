from fastapi import APIRouter, HTTPException
from app.core.responses import APIResponse
from app.services.territory.repository import TerritoryRepository

router = APIRouter()


@router.get(
    "/municipalities",
    response_model=APIResponse,
)
async def list_municipalities() -> APIResponse:
    repo = TerritoryRepository.get_instance()
    return APIResponse.ok(data=repo.get_all_municipalities())


@router.get(
    "/municipalities/{municipality_id}",
    response_model=APIResponse,
)
async def get_municipality(municipality_id: str) -> APIResponse:
    repo = TerritoryRepository.get_instance()
    m = repo.get_municipality(municipality_id)
    if not m:
        raise HTTPException(404, detail=f"Municipio '{municipality_id}' no encontrado.")
    return APIResponse.ok(data={**m, "neighborhoods": repo.get_neighborhoods_for(municipality_id)})


@router.get(
    "/neighborhoods/{municipality_id}",
    response_model=APIResponse,
)
async def list_neighborhoods(municipality_id: str) -> APIResponse:
    repo = TerritoryRepository.get_instance()
    return APIResponse.ok(data=repo.get_neighborhoods_for(municipality_id))
