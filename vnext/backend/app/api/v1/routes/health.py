from fastapi import APIRouter
from app.core.responses import APIResponse
router = APIRouter()

@router.get(
    "/",
    response_model=APIResponse,
)
async def health() -> APIResponse:
    return APIResponse.ok(data={"status": "ok"}, message="VoxPolítica vNext running.")
