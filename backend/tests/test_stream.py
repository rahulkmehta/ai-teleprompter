"""Tests for the /ws endpoint covering the mock-transcript path end-to-end.

Validates the message protocol contract (init → ready, ingest_transcript →
transcript+pointer+state) without needing real audio or Deepgram.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ws_init_returns_ready():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "script": "Hello world."})
        msg = ws.receive_json()
        assert msg["type"] == "ready"
        assert msg["token_count"] == 2


def test_ws_init_empty_script_errors():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "script": "   "})
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_ws_ingest_transcript_emits_pointer_chain():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "script": "The quick brown fox jumps."})
        assert ws.receive_json()["type"] == "ready"

        ws.send_json({
            "type": "ingest_transcript",
            "text": "The quick brown fox",
            "is_final": True,
        })

        transcript = ws.receive_json()
        pointer = ws.receive_json()
        state = ws.receive_json()

        assert transcript["type"] == "transcript"
        assert pointer["type"] == "pointer"
        assert pointer["index"] >= 3
        assert state["type"] == "state"
        assert state["status"] == "on_script"


def test_ws_ingest_before_init_errors():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({
            "type": "ingest_transcript",
            "text": "hello",
            "is_final": True,
        })
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_ws_unknown_message_type_errors():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "frobnicate"})
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_ws_off_script_state_after_garbage():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "init", "script": "The quick brown fox jumps over the lazy dog."})
        assert ws.receive_json()["type"] == "ready"

        last_state = None
        for _ in range(6):
            ws.send_json({
                "type": "ingest_transcript",
                "text": "hmm uhh okay",
                "is_final": True,
            })
            ws.receive_json()  # transcript
            ws.receive_json()  # pointer
            last_state = ws.receive_json()

        assert last_state is not None
        assert last_state["status"] == "off_script"
