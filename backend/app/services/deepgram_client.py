import asyncio
import json
import logging
import urllib.parse
from typing import Awaitable, Callable

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import settings

logger = logging.getLogger(__name__)

TranscriptCallback = Callable[[str, bool], Awaitable[None]]
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"

class DeepgramSTT:
    def __init__(self, on_transcript: TranscriptCallback):
        self._on_transcript = on_transcript
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._receive_task: asyncio.Task | None = None

    async def start(self) -> None:
        if not settings.deepgram_api_key:
            raise RuntimeError("DEEPGRAM_API_KEY not set")

        params = {
            "model": settings.deepgram_model,
            "language": settings.deepgram_language,
            "encoding": "linear16",
            "sample_rate": str(settings.sample_rate),
            "channels": "1",
            "interim_results": "true",
            "smart_format": "false",
            "punctuate": "false",
            "numerals": "false",
            "endpointing": str(settings.deepgram_endpointing_ms),
            "utterance_end_ms": str(settings.deepgram_utterance_end_ms),
            "vad_events": "true",
        }
        url = f"{DEEPGRAM_WS_URL}?{urllib.parse.urlencode(params)}"
        headers = {"Authorization": f"Token {settings.deepgram_api_key}"}

        self._ws = await websockets.connect(url, additional_headers=headers)
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    continue
                msg = json.loads(raw)
                if msg.get("type") != "Results":
                    continue
                transcript = msg["channel"]["alternatives"][0]["transcript"]
                if not transcript.strip():
                    continue
                await self._on_transcript(transcript, bool(msg.get("is_final")))
        except (asyncio.CancelledError, ConnectionClosed):
            raise
        except Exception:
            logger.exception("Deepgram receive loop error")

    async def send_audio(self, audio: bytes) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.send(audio)
        except ConnectionClosed:
            pass

    async def stop(self) -> None:
        if self._receive_task is not None:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except BaseException:
                pass
            self._receive_task = None

        if self._ws is not None:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
