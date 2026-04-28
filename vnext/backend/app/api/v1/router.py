from fastapi import APIRouter
from app.api.v1.routes import (analysis, evidence, exports, health, speech, territory)

api_router = APIRouter()
api_router.include_router(health.router,    prefix="/health",    tags=["Health"])
api_router.include_router(territory.router, prefix="/territory", tags=["Territory"])
api_router.include_router(evidence.router,  prefix="/evidence",  tags=["Evidence"])
api_router.include_router(analysis.router,  prefix="/analysis",  tags=["Analysis"])
api_router.include_router(speech.router,    prefix="/speech",    tags=["Speech"])
api_router.include_router(exports.router,   prefix="/exports",   tags=["Exports"])