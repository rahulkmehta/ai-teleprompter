# AI Teleprompter

Real-time teleprompter that auto-scrolls as you read it back, using Deepgram Nova-3 speech-to-text and a custom local-alignment algorithm that survives ad-libs, rephrasing, mispronunciation, and skipped words.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the design rationale and demo defense talking points.

## Stack

- **Backend**: FastAPI + Pydantic Settings + Deepgram SDK + rapidfuzz + jellyfish + wordfreq
- **Frontend**: React + TypeScript + Vite, AudioWorklet for raw 16kHz Int16 PCM capture
- **Transport**: single WebSocket carrying control JSON + binary PCM frames

## Setup

```bash
# 1. Install backend deps into the existing conda env
conda run -n ai-teleprompter pip install -r backend/requirements.txt

# 2. Install frontend deps
npm --prefix frontend install

# 3. Set the Deepgram API key (sign up free at deepgram.com)
cp backend/.env.example backend/.env
# edit backend/.env and set DEEPGRAM_API_KEY=...
```

## Run (two terminals)

```bash
# Terminal 1 — backend
conda run -n ai-teleprompter --no-capture-output \
  uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend
npm --prefix frontend run dev
```

Open <http://127.0.0.1:5173>. Vite proxies `/ws` → `ws://127.0.0.1:8000/ws`.

## Test

```bash
cd backend && conda run -n ai-teleprompter --no-capture-output pytest
```

37 tests, ~1s. Covers tokenizer, all four alignment failure modes (ad-lib, mispronunciation, rephrasing, skipped sentence), guardrails (forward-jump cap, sentence monotonicity, confidence floor), full-script re-anchor, and the WebSocket message protocol.

## Project layout

```
backend/
  app/
    api/stream.py            WebSocket endpoint, message routing
    core/config.py           pydantic-settings (DEEPGRAM_API_KEY, alignment knobs)
    schemas/messages.py      WS message types
    services/
      tokenizer.py           normalize + Metaphone + IDF (via wordfreq)
      aligner.py             score / align / Aligner — the heart of the system
      deepgram_client.py     LiveTranscription wrapper
    main.py                  FastAPI app + CORS + router mount
  tests/                     37 tests
  pytest.ini, requirements.txt, .env.example
frontend/
  public/pcm-worklet.js      AudioWorkletProcessor (downsample + Int16 PCM)
  src/
    App.tsx                  state machine: idle / starting / recording / stopping
    Editor.tsx               script-entry view
    Teleprompter.tsx         word-spans + transform-based smooth scroll
    audio.ts                 PCMCapture: getUserMedia → AudioContext → worklet
    ws.ts                    WSClient with typed handlers
    types.ts                 ServerMessage union, mirrors backend schemas
ARCHITECTURE.md              design rationale + demo Q&A
```

## How it works (one paragraph)

The browser captures mic audio in an AudioWorklet, downsamples to 16kHz Int16, and sends 50ms binary frames over a WebSocket. The FastAPI backend forwards them to Deepgram Nova-3 streaming. As Deepgram emits interim and final transcript events, the `Aligner` runs Smith-Waterman local alignment between a rolling 8-token transcript buffer and a 20-token forward window of script tokens. Token-pair similarity combines exact match, Double-Metaphone-ish phonetic equivalence, and Levenshtein distance, all weighted by IDF rarity from `wordfreq` so common words don't dominate. Three guardrails — forward-jump cap, sentence-bounded monotonicity, and a confidence floor — keep the pointer from teleporting on coincidental matches. After 5 consecutive low-confidence events the aligner falls back to a full-script re-anchor search. The pointer index streams back to the browser, which sets a CSS `transform: translateY()` target on the script container; a 200ms transition handles the smooth scroll, keeping the current word at ~25% from the top of a 4-line viewport.

## Out of scope (next steps)

- Backward re-anchor (user says "let me start over from the top")
- Number normalization ("$500" ↔ "five hundred dollars")
- Production deployment (token-minted Deepgram auth, rate limiting)
- Pause/resume mid-session, WPM display, saved scripts
- Mobile/touch UI, accessibility audit
