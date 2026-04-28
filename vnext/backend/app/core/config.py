from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "VoxPolítica"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./voxpolitica.db"
    DATABASE_URL_SYNC: str = "sqlite:///./voxpolitica.db"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT_SECONDS: int = 60
    GROQ_MAX_TOKENS: int = 4096
    GROQ_TEMPERATURE: float = 0.7

    INEGI_API_TOKEN: str = ""
    BANXICO_TOKEN: str = ""

    EVIDENCE_CACHE_TTL_DAYS: int = 180
    ANALYSIS_CACHE_TTL_DAYS: int = 90
    BATCH_MAX_CONCURRENCY: int = 5

    SPEECH_WORDS_PER_MINUTE: int = 130
    SPEECH_MIN_WORDS_FACTOR: float = 0.75
    SPEECH_MAX_RETRY_ATTEMPTS: int = 1
    SPEECH_SECTIONED_MIN_MINUTES: int = 8
    SPEECH_OUTLINE_RETRY_ATTEMPTS: int = 1
    SPEECH_SECTION_RETRY_ATTEMPTS: int = 1
    SPEECH_DEFAULT_BODY_SECTIONS: int = 2
    SPEECH_OPENING_WORDS: int = 180
    SPEECH_CLOSING_WORDS: int = 160
    SPEECH_SECTION_WORDS: int = 450
    SPEECH_SECTION_MIN_FACTOR: float = 0.75
    SPEECH_MODEL_MAX_OUTPUT_TOKENS: int = 5000
    SPEECH_LONG_FORM_SECTION_CAP: int = 16
    SPEECH_LONG_FORM_BATCH_SIZE: int = 4
    SPEECH_DURATION_TOLERANCE_PCT: float = 0.18
    SPEECH_DURATION_TOLERANCE_MINUTES: float = 1.0

    SOURCE_TEXT_MIN_WORDS: int = 40
    SOURCE_TEXT_MAX_CHARS: int = 200000
    SOURCE_TEXT_SEGMENT_WORDS: int = 850
    SOURCE_TEXT_SEGMENT_OVERLAP_WORDS: int = 60
    SOURCE_TEXT_PROMPT_BUDGET_WORDS: int = 2600
    SOURCE_TEXT_MIN_ALPHA_RATIO: float = 0.55

    MAX_UPLOAD_SIZE_MB: int = 10

    @field_validator("GROQ_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("GROQ_TEMPERATURE must be 0.0–2.0")
        return v

    @field_validator(
        "SPEECH_MIN_WORDS_FACTOR",
        "SPEECH_SECTION_MIN_FACTOR",
        "SPEECH_DURATION_TOLERANCE_PCT",
        "SOURCE_TEXT_MIN_ALPHA_RATIO",
    )
    @classmethod
    def validate_word_factor(cls, v: float) -> float:
        if not 0.1 <= v <= 1.0:
            raise ValueError("Speech/text factors must be between 0.1 and 1.0")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()