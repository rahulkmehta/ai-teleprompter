import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.messages import (
    ErrorMessage,
    IngestTranscriptMessage,
    InitMessage,
    PointerMessage,
    ReadyMessage,
    StateMessage,
    TranscriptMessage,
)
from app.services.aligner import Aligner, AlignmentResult
from app.services.deepgram_client import DeepgramSTT
from app.services.tokenizer import tokenize_script

logger = logging.getLogger(__name__)
router = APIRouter()

async def _send(ws: WebSocket, msg: BaseModel) -> None:
    await ws.send_text(msg.model_dump_json())

async def _emit_alignment(
    ws: WebSocket, transcript: str, is_final: bool, result: AlignmentResult
) -> None:
    await _send(ws, TranscriptMessage(text=transcript, is_final=is_final))
    await _send(
        ws,
        PointerMessage(
            index=result.pointer,
            confidence=result.confidence,
            tentative=result.tentative,
        ),
    )
    await _send(ws, StateMessage(status=result.state))


@router.websocket("/ws")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    aligner: Aligner | None = None
    stt: DeepgramSTT | None = None
    stt_failed = False

    async def on_transcript(text: str, is_final: bool) -> None:
        if aligner is None:
            return
        result = aligner.process(text, is_final)
        await _emit_alignment(ws, text, is_final, result)

    try:
        while True:
            event = await ws.receive()

            if event.get("type") == "websocket.disconnect":
                break

            if "text" in event:
                try:
                    data = json.loads(event["text"])
                except json.JSONDecodeError:
                    await _send(ws, ErrorMessage(message="invalid JSON"))
                    continue

                msg_type = data.get("type")

                if msg_type == "init":
                    try:
                        init = InitMessage(**data)
                    except ValidationError as e:
                        await _send(ws, ErrorMessage(message=f"invalid init: {e.errors()}"))
                        continue

                    script = tokenize_script(init.script)
                    if len(script) == 0:
                        await _send(ws, ErrorMessage(message="empty script"))
                        continue

                    aligner = Aligner(script=script, config=settings)
                    await _send(ws, ReadyMessage(token_count=len(script)))

                elif msg_type == "stop":
                    break

                elif msg_type == "ingest_transcript":
                    if aligner is None:
                        await _send(ws, ErrorMessage(message="not initialized"))
                        continue
                    try:
                        ingest = IngestTranscriptMessage(**data)
                    except ValidationError as e:
                        await _send(ws, ErrorMessage(message=f"invalid transcript: {e.errors()}"))
                        continue
                    result = aligner.process(ingest.text, ingest.is_final)
                    await _emit_alignment(ws, ingest.text, ingest.is_final, result)

                else:
                    await _send(ws, ErrorMessage(message=f"unknown message type: {msg_type}"))

            elif "bytes" in event:
                if aligner is None:
                    continue

                if stt is None and not stt_failed:
                    if settings.deepgram_api_key:
                        try:
                            stt = DeepgramSTT(on_transcript=on_transcript)
                            await stt.start()
                        except Exception as e:
                            logger.exception("Failed to start Deepgram")
                            await _send(
                                ws,
                                ErrorMessage(
                                    message=f"STT unavailable: {e}",
                                    recoverable=True,
                                ),
                            )
                            stt = None
                            stt_failed = True
                    else:
                        stt_failed = True
                        await _send(
                            ws,
                            ErrorMessage(
                                message="DEEPGRAM_API_KEY not configured; audio frames ignored",
                                recoverable=True,
                            ),
                        )

                if stt is not None:
                    await stt.send_audio(event["bytes"])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WebSocket session error")
        try:
            await _send(ws, ErrorMessage(message=f"server error: {e}", recoverable=False))
        except Exception:
            pass
    finally:
        if stt is not None:
            await stt.stop()
