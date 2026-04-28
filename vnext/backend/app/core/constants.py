"""Project-wide constants — VoxPolítica 2.0"""
import json
from pathlib import Path

_sv_path = Path(__file__).parent.parent / "data" / "reference" / "schema_version.json"
try:
    with open(_sv_path) as _f:
        _sv = json.load(_f)
    MUNICIPALITIES_COUNT: int = _sv["municipalities_count"]
    SCHEMA_VERSION: str = _sv["hash"]
except Exception:
    MUNICIPALITIES_COUNT = 60
    SCHEMA_VERSION = "unknown"

STATE_NAME = "Tlaxcala"
STATE_ID = "TLX"
WORDS_PER_MINUTE = 130
SPEECH_MIN_WORDS_FACTOR = 0.85