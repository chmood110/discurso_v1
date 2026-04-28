# VoxPolítica

Plataforma de inteligencia territorial y comunicación política para **57 municipios del estado de Tlaxcala**, México.

**Versión:** `1.0.0`  
**Stack:** Python 3.11 · FastAPI 0.115 · SQLAlchemy 2 async · Next.js 14 · TypeScript strict

---

## Cobertura territorial

Tlaxcala tiene 60 municipios oficiales (INEGI Marco Geoestadístico 2023).
**Este dataset cubre 57 de esos 60.** Los 3 municipios restantes no están incluidos en los datos de referencia actuales. El sistema rechaza solicitudes para IDs de municipios fuera del dataset.

Las constantes `MUNICIPALITIES_COUNT` (57) y `SCHEMA_VERSION` se derivan de `app/data/reference/schema_version.json` — cambiar el dataset actualiza todo el sistema automáticamente.

---

## Arranque rápido

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # editar GROQ_API_KEY
python -m scripts.seed         # carga 57 municipios en SQLite
uvicorn app.main:app --reload --port 8000

# Frontend (terminal separada)
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

API docs: http://localhost:8000/docs

---

## Variables de entorno

### `backend/.env`

| Variable | Descripción | Requerida |
|---|---|---|
| `APP_ENV` | `development` / `staging` / `production` | No (default: development) |
| `GROQ_API_KEY` | API key Groq — https://console.groq.com | Sí (para generación IA) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./voxpolitica.db` para dev | No |
| `GROQ_MODEL` | Modelo Groq | No (default: llama-3.3-70b-versatile) |

Sin `GROQ_API_KEY`, los endpoints de generación devuelven fallback estructural (sin IA). El sistema es funcional para análisis de evidencia, PDF y batch sin clave.

---

## Política de esquema y arranque

| Entorno | Comportamiento |
|---|---|
| `APP_ENV=development` | `create_tables()` crea el esquema automáticamente al iniciar |
| `APP_ENV=staging` o `production` | Alembic es el único gestor de esquema. Ejecutar `alembic upgrade head` antes de iniciar |

Un valor de `APP_ENV` no reconocido lanza `RuntimeError` en startup. No hay comportamiento ambiguo.

```bash
# Producción
export APP_ENV=production
alembic upgrade head
uvicorn app.main:app --port 8000
```

---

## Contratos API

Todos los endpoints POST que generan recursos devuelven **Detail** (payload completo).  
Los endpoints GET `/latest` devuelven **Summary** (identificadores + calidad + estado de validación).

| Endpoint | Método | Devuelve |
|---|---|---|
| `/evidence/resolve/{id}` | POST | `EvidenceDetail` |
| `/evidence/latest/{id}` | GET | `EvidenceSummary` |
| `/analysis/run` | POST | `AnalysisDetail` |
| `/analysis/latest/{id}` | GET | `AnalysisSummary` |
| `/analysis/history/{id}` | GET | `list[AnalysisSummary]` |
| `/brief/run` | POST | `BriefDetail` |
| `/brief/latest/{id}` | GET | `BriefSummary` |
| `/speech/run` | POST | `SpeechDetail` |
| `/speech/latest/{id}` | GET | `SpeechSummary` |
| `/speech/review` | POST | `ReviewDetail` (persisted) |
| `/batch/analysis` | POST | `BatchJobOut` (async) |
| `/batch/brief` | POST | `BatchJobOut` (async) |
| `/batch/speech` | POST | `BatchJobOut` (async) |
| `/batch/{job_id}` | GET | `BatchJobOut` |
| `/batch/{job_id}/export` | GET | ZIP binario |
| `/exports/pdf/analysis/{id}` | GET | PDF binario |
| `/exports/pdf/brief/{id}` | GET | PDF binario |
| `/exports/pdf/speech/{id}` | GET | PDF binario |
| `/territory/municipalities` | GET | `list[Municipality]` |
| `/territory/municipalities/{id}` | GET | `Municipality` |
| `/territory/neighborhoods/{id}` | GET | `list[Neighborhood]` |
| `/health/` | GET | status |

**`force_refresh`** siempre en el body JSON (nunca query param):
```json
POST /evidence/resolve/TLX-APZ
{"force_refresh": true}
```

---

## Calidad de datos

### Qué almacena cada recurso

| Recurso | `data_quality` type | Campos disponibles |
|---|---|---|
| `EvidenceDetail` | `DataQualitySummary` | `overall_confidence`, `municipal_coverage_pct`, `state_coverage_pct`, `estimated_coverage_pct`, `can_cite_as_municipal`, `quality_label`, `methodology_disclaimer` |
| `AnalysisDetail` / `Summary` | `DataQualityBrief` | `overall_confidence`, `can_cite_as_municipal` |
| `BriefDetail` / `Summary` | `DataQualityBrief` | `overall_confidence`, `can_cite_as_municipal` |
| `SpeechDetail` / `Summary` | `DataQualityBrief` | `overall_confidence`, `can_cite_as_municipal=false` |

`DataQualitySummary` (7 campos, desglose de cobertura por tipo) **solo está disponible en `EvidenceDetail`**.  
Para obtener el `methodology_disclaimer` completo o `quality_label`, obtener `EvidenceDetail` vía `POST /evidence/resolve/{id}`.

### Cobertura de datos por municipio

| Nivel | Municipios | Fuente |
|---|---|---|
| `official_municipal` | 6 | INEGI Censo 2020 + CONEVAL 2020 directo |
| `calibrated_estimate` | 51 | Estimaciones por región/categoría Tlaxcala |

Cuando `can_cite_as_municipal=false`, los PDFs muestran automáticamente la nota metodológica de EvidenceDetail.  
**No hay campos `quality_label` o `methodology_disclaimer` en Analysis/Brief/Speech** — esos campos viven en Evidence.

---

## Política de validación

- `OutputValidationPipeline.RULE_VERSION = "1.0.0"` — versionado explícito.
- Un output con errores bloqueantes (`blocking_count > 0`) **no se persiste con `status=completed`**.
- Se guarda `validation_blocked=True` en la fila para trazabilidad.
- `validation_rule_version` se persiste en cada run (brief, speech, analysis).
- El campo `validation.issues` en la respuesta lista exactamente qué reglas fallaron.

---

## Batch processing

Cada tarea batch abre su propia `AsyncSessionLocal()`. La sesión del request HTTP se usa únicamente para crear el `BatchJobDB` inicial. No hay riesgo de `DetachedInstanceError` bajo concurrencia real.

---

## Limitaciones actuales

- 3 municipios de Tlaxcala (de 60 oficiales) no están en el dataset.
- No hay autenticación de usuarios.
- Los PDFs no tienen encabezado con logo personalizado.
- La migración 002 debe ejecutarse manualmente antes de usar parámetros de caché de brief/speech en entornos con base de datos existente.
- `GROQ_MAX_TOKENS = 4096`; discursos de 60 min (~7800 palabras) pueden requerir múltiples llamadas — no implementado aún.

---

## Migraciones

```bash
# Desarrollo inicial (ya cubierto por create_tables)
python -m scripts.seed

# Aplicar hardening (entornos con DB preexistente)
alembic upgrade head
# Equivale a: 001_initial.py + 002_hardening.py
```

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 · FastAPI 0.115 · SQLAlchemy 2 async · Alembic |
| Base de datos | SQLite (dev) · PostgreSQL (prod) |
| LLM | Groq API (llama-3.3-70b-versatile) |
| PDF | ReportLab |
| Frontend | Next.js 14 App Router · TypeScript strict · Tailwind CSS · Zustand |

---

## Testing

```bash
cd backend
pip install -r requirements.txt   # includes pytest, pytest-asyncio, httpx

# All tests
pytest tests/ -v

# By category
pytest tests/unit/        -v   # Validation pipeline, parameter hashing  (~1s)
pytest tests/contracts/   -v   # API shape verification                   (~5s)
pytest tests/integration/ -v   # DB, cache, PDF, batch                    (~8s)
pytest tests/regression/  -v   # Bug regression guards                    (~5s)

# Single module
pytest tests/contracts/test_api_contracts.py -v
pytest tests/regression/test_regression_suite.py -v
```

Test DB: `./test_voxpolitica.db` (created/deleted automatically per session).

