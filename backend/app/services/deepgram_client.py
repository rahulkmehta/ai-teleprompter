"""Deepgram LiveTranscription wrapper, owned by stream.py during a live session.

Audio frames from the browser's AudioWorklet flow in via send_audio(); transcript
events flow back out to a caller-provided async callback that feeds
Aligner.process().

Connects directly to wss://api.deepgram.com/v1/listen using `websockets` rather
than the deepgram-sdk. Reason: the SDK 6.x serializes Python booleans as
"True"/"False" (capitalized) in URL query params, but Deepgram requires lowercase
"true"/"false" per JSON convention — every connect attempt returned HTTP 400.
The protocol itself is simple enough that bypassing the SDK is cleaner than
working around its encoder bug.

Configuration pulled from app.core.config: model nova-3, encoding linear16 at
16kHz, interim_results=true (sub-200ms tentative-pointer updates),
smart_format/punctuate/numerals=false so the transcript is a raw word stream
that mirrors how the script is tokenized.
"""
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
            pass  # receive loop will surface the disconnect

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
