from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"
    deepgram_language: str = "en-US"
    deepgram_endpointing_ms: int = 25
    deepgram_utterance_end_ms: int = 1000

    sample_rate: int = 16000
    chunk_ms: int = 10

    window_size: int = 20
    buffer_size: int = 8
    confidence_floor: float = 0.4
    max_forward_jump: int = 5
    re_anchor_streak: int = 5
    re_anchor_confidence: float = 0.6
    alpha_exact: float = 0.5
    beta_phonetic: float = 0.3
    gamma_levenshtein: float = 0.2

    allowed_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
