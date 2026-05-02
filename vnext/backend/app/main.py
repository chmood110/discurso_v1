"""
VoxPolítica vNext — FastAPI application.

Startup schema policy:
  APP_ENV=development  → create_tables() auto-creates schema (no Alembic required)
  APP_ENV=production   → schema managed exclusively by Alembic
                         Must run: alembic upgrade head before starting server
  APP_ENV=staging      → same as production

Never mix create_tables() and Alembic in the same environment.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.connection import create_tables
from app.services.territory.repository import TerritoryRepository

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VoxPolítica vNext env=%s", settings.APP_ENV)

    if settings.APP_ENV == "development":
        await create_tables()
        logger.info("Development: schema auto-created via create_tables()")
    elif settings.APP_ENV in ("staging", "production"):
        logger.info(
            "%s: schema managed by Alembic. "
            "Ensure 'alembic upgrade head' has been run.",
            settings.APP_ENV,
        )
    else:
        raise RuntimeError(f"Unknown APP_ENV value: '{settings.APP_ENV}'. Must be development|staging|production.")

    _ = TerritoryRepository.get_instance()
    logger.info("Territory repository ready")
    yield
    logger.info("Shutting down VoxPolítica vNext")


app = FastAPI(
    title="VoxPolítica vNext",
    description=(
        "Plataforma de inteligencia territorial y comunicación política. "
        "Cubre 57 de los 60 municipios del estado de Tlaxcala, México."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    return {"name": "VoxPolítica vNext", "version": "1.0.0", "status": "running"}
