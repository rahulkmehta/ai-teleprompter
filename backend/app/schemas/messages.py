from typing import Literal

from pydantic import BaseModel


class InitMessage(BaseModel):
    type: Literal["init"]
    script: str


class StopMessage(BaseModel):
    type: Literal["stop"]


class IngestTranscriptMessage(BaseModel):
    """Client-side transcript injection for mock testing without audio."""

    type: Literal["ingest_transcript"]
    text: str
    is_final: bool


class ReadyMessage(BaseModel):
    type: Literal["ready"] = "ready"
    token_count: int


class PointerMessage(BaseModel):
    type: Literal["pointer"] = "pointer"
    index: int
    confidence: float
    tentative: bool


class TranscriptMessage(BaseModel):
    type: Literal["transcript"] = "transcript"
    text: str
    is_final: bool


class StateMessage(BaseModel):
    type: Literal["state"] = "state"
    status: Literal["on_script", "off_script", "idle"]


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
    recoverable: bool = False
