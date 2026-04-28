"""
Test configuration for VoxPolítica 1.0.0.
Uses a file-based SQLite test DB so all fixtures share the same data.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# File-based test DB — shared across the session
TEST_DB_URL = "sqlite+aiosqlite:///./test_voxpolitica.db"
TEST_DB_SYNC = "sqlite:///./test_voxpolitica.db"

_DATA_DIR = Path(__file__).parent.parent / "app" / "data" / "reference"
_MUNICIPALITIES = json.loads((_DATA_DIR / "municipalities.json").read_text(encoding="utf-8"))

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Session-scoped engine. Creates tables and seeds municipalities once."""
    from app.db.connection import Base
    from app.models import db_models  # ensure all models are imported

    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed municipalities (idempotent)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionFactory() as s:
        for m in _MUNICIPALITIES:
            await s.execute(
                text(
                    "INSERT OR IGNORE INTO municipalities "
                    "(id, name, state_id, population_approx, category, region) "
                    "VALUES (:id, :name, :state_id, :pop, :cat, :reg)"
                ),
                {
                    "id": m["id"], "name": m["name"],
                    "state_id": m.get("state_id", "TLX"),
                    "pop": m.get("population_approx", 0),
                    "cat": m.get("category", "municipio_rural"),
                    "reg": m.get("region", "Valle Central"),
                },
            )
        await s.commit()

    yield engine

    await engine.dispose()
    import os
    try: os.remove("./test_voxpolitica.db")
    except FileNotFoundError: pass


@pytest.fixture(scope="session")
def session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Per-test session. Does NOT roll back so that cross-fixture state is visible."""
    async with session_factory() as session:
        yield session


@pytest.fixture
def seeded_db(db_session):
    """DB session with 57 municipalities already present (seeded at session scope)."""
    return db_session


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB overridden to test engine."""
    from app.main import app
    from app.db.connection import get_db

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def mock_groq(monkeypatch):
    """Replace GroqClient.complete with a deterministic fake that always passes validation."""
    from app.services.llm import groq_client as gc
    import json as _json

    async def fake_complete(self, request):
        # Build text that satisfies 85% of 5-min target (552+ words)
        base = (
            "Ciudadanas y ciudadanos de Apizaco, hoy vengo a hablar de trabajo digno, "
            "justicia social y el futuro que merecen las familias de este municipio. "
            "El 28.6% de nuestra población vive en pobreza multidimensional. "
            "El 42% de los trabajadores no tiene prestaciones de ley. "
            "Esta realidad exige acción concreta, no promesas vacías. "
        )
        long_text = base * 60  # ~600 words

        payload = {
            "executive_summary": (
                "Apizaco es un municipio industrial con 28.6% de pobreza multidimensional "
                "y una informalidad laboral del 42%. La oportunidad central está en "
                "formalizar el empleo del clúster textil y garantizar seguridad social real."
            ),
            "territory_context": "Apizaco, Tlaxcala — Valle Central",
            "key_findings": [
                "Alta informalidad laboral en manufactura textil (42% de la PEA)",
                "Rezago en acceso a salud especializada",
            ],
            "pain_points": [
                "Trabajadores sin prestaciones ni seguridad social",
                "Largas esperas en servicios de salud",
            ],
            "messaging_axes": [{
                "axis": "Trabajo digno",
                "message": "Apizaco merece empleos con contrato, prestaciones y seguridad social real.",
                "rationale": "El 42% de informalidad genera inseguridad cotidiana",
            }],
            "recommended_tone": "combativo y propositivo",
            "opportunities": ["Clúster textil certificable"],
            "emotional_hooks": ["El esfuerzo de madres trabajadoras merece reconocimiento"],
            "rational_hooks": ["Cada peso en seguridad social genera retorno fiscal"],
            "risk_flags": [],
            "candidate_positioning": "Candidata del trabajo digno con propuestas financiadas.",
            "next_steps": ["Visita industrial zona norte"],
            "call_to_action_lines": ["Firma el convenio de formalización"],
            "title": "Arranque de campaña — Apizaco",
            "speech_objective": "Movilizar apoyo ciudadano en la zona industrial",
            "target_audience": "Trabajadoras y trabajadores textiles de Apizaco",
            "estimated_duration_minutes": 5,
            "opening": base * 3,
            "body_sections": [{
                "title": "Diagnóstico territorial",
                "content": long_text,
                "persuasion_technique": "Validación con datos verificados",
            }],
            "closing": (
                "Juntos vamos a transformar Apizaco. Voto a voto, colonia a colonia. "
                "El cambio real empieza aquí y empieza hoy. ¡Adelante, Apizaco! "
            ) * 5,
            "full_text": long_text,
            "local_references": ["Zona industrial norte", "Mercado Hidalgo"],
            "adaptation_notes": [],
            "overall_score": 7.5,
            "overall_assessment": "Discurso bien territorializado con buen balance.",
            "strengths": ["Clara identificación del municipio", "Tono apropiado"],
            "weaknesses": ["El cierre podría ser más contundente"],
        }
        resp = MagicMock()
        resp.content = _json.dumps(payload)
        return resp

    monkeypatch.setattr(gc.GroqClient, "complete", fake_complete)
    return fake_complete


# ── Sample data constants ─────────────────────────────────────────────────────
VALID_MUN_ID     = "TLX-APZ"    # Apizaco — official_municipal data
ESTIMATED_MUN_ID = "TLX-AMA"    # Amaxac  — calibrated_estimate
SECOND_MUN_ID    = "TLX-HMT"    # Huamantla

VALID_BRIEF_PARAMS = {
    "municipality_id": VALID_MUN_ID,
    "campaign_objective": "Ganar la presidencia municipal de Apizaco en 2024",
    "force_refresh": False,
}

VALID_SPEECH_PARAMS = {
    "municipality_id": VALID_MUN_ID,
    "speech_goal": "Movilizar apoyo ciudadano en la zona industrial de Apizaco",
    "audience": "Trabajadoras y trabajadores textiles de Apizaco",
    "tone": "combativo y propositivo",
    "channel": "mitin",
    "duration_minutes": 5,
    "force_refresh": False,
}
