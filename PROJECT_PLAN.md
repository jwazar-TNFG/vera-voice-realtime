# Vera Voice Realtime — Project Plan

**Goal:** Sub-second latency voice conversation with Vera using OpenAI's Realtime API

**Created:** 2026-04-28

---

## Why Realtime?

Current stack (Whisper → Claude → ElevenLabs) has 3 API round-trips:
1. Audio → Whisper (transcribe) — ~1-2s
2. Text → Claude (generate) — ~1-2s  
3. Text → ElevenLabs (TTS) — ~1-2s

**Total latency: 3-6 seconds**

OpenAI Realtime API handles voice-in → voice-out in a single WebSocket stream:
- Native audio understanding (no STT step)
- Streaming response generation
- Streaming audio output
- Built-in interruption handling

**Target latency: <500ms**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Frontend)                   │
│  ┌─────────────┐                    ┌─────────────────┐ │
│  │ Microphone  │───WebSocket────────▶│  Audio Player  │ │
│  └─────────────┘        │            └─────────────────┘ │
└─────────────────────────│───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Backend (WebSocket Relay)                   │
│                                                          │
│  Browser ◄──► Railway Server ◄──► OpenAI Realtime API   │
│                                                          │
│  - Authenticates with OpenAI                            │
│  - Relays audio frames                                   │
│  - Handles session management                            │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Vanilla JS + Web Audio API + WebSocket |
| **Backend** | Python FastAPI + websockets |
| **Voice AI** | OpenAI Realtime API (gpt-4o-realtime-preview) |
| **Hosting** | Vercel (frontend) + Railway (backend) |
| **Wake Word** | Picovoice Porcupine (reuse from v1) |

---

## OpenAI Realtime API Overview

**Endpoint:** `wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17`

**Key Features:**
- Bidirectional audio streaming
- Function calling support (connect to real Vera later)
- Native interruption detection
- Voice activity detection (VAD) built-in
- Multiple voices available

**Audio Format:**
- Input: PCM 16-bit, 24kHz, mono
- Output: PCM 16-bit, 24kHz, mono (or G.711, Opus)

**Pricing (as of 2026):**
- Audio input: $0.06 / minute
- Audio output: $0.24 / minute
- Text input: $5 / 1M tokens
- Text output: $20 / 1M tokens

---

## Phase 1: Basic Connection (Day 1)

- [ ] Set up backend WebSocket relay
- [ ] Connect browser to backend via WebSocket
- [ ] Backend connects to OpenAI Realtime API
- [ ] Test basic audio round-trip
- [ ] Deploy to Railway

**Deliverable:** Say something → hear GPT-4o respond

---

## Phase 2: Voice UI (Day 2)

- [ ] Design clean voice-first UI
- [ ] Add visual feedback (listening, processing, speaking)
- [ ] Integrate Porcupine wake word ("Hey Vera")
- [ ] Add conversation mode (continuous listening)
- [ ] Handle interruptions

**Deliverable:** Full voice conversation with visual feedback

---

## Phase 3: Vera Integration (Day 3+)

- [ ] Add system prompt for Vera personality
- [ ] Implement function calling for Vera tools
- [ ] Connect to OpenClaw API (with Jon's auth approach)
- [ ] Handle file/data requests ("Show me top reps")
- [ ] Route outputs appropriately (voice vs Telegram)

**Deliverable:** Real Vera capabilities via voice

---

## API Keys Required

| Service | Status |
|---------|--------|
| OpenAI (Realtime API) | Need to verify Humberto has access |
| Picovoice | ✅ Already have |

**Note:** OpenAI Realtime API may require specific account tier. Check at https://platform.openai.com/

---

## Files

```
vera-voice-realtime/
├── PROJECT_PLAN.md          # This file
├── frontend/
│   ├── index.html           # Voice UI
│   └── vera-icon.jpg        # Reuse from v1
└── backend/
    ├── main.py              # WebSocket relay server
    ├── requirements.txt     # Dependencies
    └── .env.example         # Environment variables template
```

---

## References

- [OpenAI Realtime API Guide](https://platform.openai.com/docs/guides/realtime)
- [OpenAI Realtime API Reference](https://platform.openai.com/docs/api-reference/realtime)
- [WebSocket Audio Streaming](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

---

## Status

**Current:** Planning
**Next:** Verify OpenAI Realtime API access, then start Phase 1
