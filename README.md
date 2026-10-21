# EasyVideo — marketing-first Reel studio

Intent → shot list → upload footage → footage audit → five different Reel previews → choose three → offline narrated final exports.

A free local-first app for making organic Instagram marketing videos from authentic product clips. Designed for modest Windows laptops with 8 GB RAM and no dedicated GPU: no mandatory cloud service, watermark or paid API.

**EasyVideo is a CPU-based video editor, not a generative video model.** It does not fabricate product imagery. Initial concepts are a deterministic, documented marketing template engine; users label clips and visual content is not verified by AI.

## Windows quick start

1. Install Python 3.11+ and FFmpeg; add ffmpeg and ffprobe to PATH.
2. Clone or download this repository.
3. Double-click start-windows.bat. On its first run, this installs three small Python packages in a local virtual environment.
4. The application opens at http://127.0.0.1:8000

Windows' built-in SAPI speech system generates local voiceovers at no API cost. For better neural narration, install the Piper voice tool and download a voice model separately. Check voice-model licenses before commercial use.

## Optional Piper voice

Install with pip install piper-tts. Download a Piper ONNX voice and its matching JSON configuration file. Configure EASYVIDEO_PIPER_MODEL with the ONNX file path, and make the piper command available on PATH. Piper is used first if configured; Windows SAPI is the Windows fallback. Linux supports eSpeak or eSpeak-NG as a fallback.

Voice synthesis is local after the optional model download. Voices differ in quality and terms of use.

## Linux/macOS

Install Python 3.11+, FFmpeg, and a supported offline voice engine. Create a venv, install requirements.txt, then run:

    python -m uvicorn easyvideo.server:app --host 127.0.0.1 --port 8000

## Workflow

1. Describe the marketing intent, buyer, product facts, CTA, and optionally paste a ChatGPT narration.
2. Receive an intent-aware shot list. Hero and detail shots are mandatory; bulk office campaigns also need inventory footage.
3. Upload and label footage. FFprobe validates format, dimensions, duration, and orientation; the audit flags missing required shot roles.
4. Render five previews: STOMP, Cinematic, Smart Buyer, Office Solutions, and Social Native.
5. Select up to three Reels to export as H.264/AAC MP4 at 1080 x 1920, then post manually.

Drafts are 540 x 960 and final exports are 1080 x 1920. FFmpeg uses sequential renders with two encoder threads to be practical on an 8 GB CPU laptop. Keep adequate disk space.

## Marketing and creative rules

- The first seconds need a relevant visual or text hook.
- Cuts and meaningful progression should support retention, not just speed.
- Present verified, truthful product features and inventory.
- Use useful product details and office-buyer scenarios to encourage sharing.
- End with a genuine enquiry CTA and evaluate conversion as well as watch metrics.
- Vary marketing angle and visual direction instead of copying the same ad five times.
- Every render uses offline voiceover and original synthesized percussion. No downloaded copyrighted music.

## Phase status

| Phase | Outcome | Status |
|---|---|---|
| 1 | Intent-first creative brief, five concepts and shot list | Implemented |
| 2 | Upload, manual shot labelling, metadata check and missing-shot flags | Implemented |
| 3 | Sequential CPU video rendering, five edits and offline narration | Implemented baseline |
| 4 | Preview, select up to three and export | Implemented baseline |
| 5 | Richer kinetic typography, editable timeline and optional local LLM | Future |
| 6 | Organic Reel performance entry and recommendation engine | Future |

## Important limitations

- Single-user localhost-only app; **never expose it directly to the public Internet**.
- Footage roles are user supplied. Media validation does not establish whether the correct chair or feature actually appears.
- Missing essential footage blocks rendering. Missing optional footage may fall back to available shots; review before posting.
- User-provided product facts and scripts must be verified before publication.
- The script planner is deterministic, with five distinct templates, not a hosted or local generative model.
- No automatic Instagram posting, account access, scraping, copyrighted music library or guaranteed organic reach.
- Initial templates are a practical editing baseline, not a complete high-end human cinematography replacement.

## Tests

Install requirements-dev.txt, then run:

    python -m pytest -q

CI also uses real FFmpeg video and synthetic voice generation to smoke-test CPU rendering.

## Layout

- easyvideo/creative.py: intent, concepts, shot list and coverage rules
- easyvideo/server.py: FastAPI, local SQLite, upload/preview/export endpoints and queue
- easyvideo/voice.py: offline Piper, Windows SAPI and eSpeak engines
- easyvideo/render.py: original footage editing, synthesized percussion, H.264/AAC rendering
- web/: lightweight local client
- tests/: unit, API and encoder integration checks

Local projects are stored in easyvideo-data/ (ignored by Git). Override the directory with EASYVIDEO_DATA_DIR. The UI requests Google Fonts when online and falls back to system fonts offline.
