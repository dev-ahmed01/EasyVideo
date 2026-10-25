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

Local projects are stored in easyvideo-data/ (ignored by Git). Override the directory with EASYVIDEO_DATA_DIR. The interface optionally requests Bricolage Grotesque and Poppins from Google Fonts when online and falls back to installed system fonts offline. Rendering, voiceovers and video files remain local. To prevent all third-party font requests, remove the Google Fonts links in web/index.html.

## Organic performance tracking

After publishing, enter Reel views, reach, average watch time, shares, saves and real enquiries in the Reel Studio. Results are retained locally by project and format. The interface displays shares per 1,000 reached and enquiry counts, without claiming to predict virality. Posting and retrieving Instagram insights remain manual.

## Export refinements

Style-specific animated text, percussive punctuation, and restrained accent marks are rendered by FFmpeg without a GPU. Selected Reels are saved in the local project database so work survives a restart. For each creative, the editor provides an organic post caption to copy. Preview approval is required before final-resolution export.

## Using a ChatGPT draft script

Paste your script in the brief. The script is included across all five narrated treatments, while the openings, editing rhythm and shot sequence are independently chosen. Long scripts are shortened to suit the initial short-form templates; always review the exact narration text in each creative card before export.

## Remix a previously published Reel

Start from **Remix a Reel**, enter intent, upload the original video on the Footage screen, and assign visual clips to the required roles. Original audio is previewable in the browser. Choose either **Original Reel audio** (start + duration, 8–90 seconds within that track) or **New voiceover** (offline TTS), then export the edited visuals in any of five formats. Original audio is a mixed track — voice, music and sound effects are not separated. Ensure reuse rights for any music. The source video remains on the local computer.

## Design update

Minimal three-screen workflow: Direction, Footage, Reel Lab. Two type families: Bricolage Grotesque for display, Poppins for body; externally loaded fonts are optional, with offline system fallbacks. The app never uploads video to an external server.

## Pick visual moments from an old Reel

While reviewing the original Reel in **Footage**, enter a timestamp, duration and the actual visual role, then choose **Add selected moment**. EasyVideo extracts a new editable clip with FFmpeg. Repeat for hero, details, workspace or stock shots, then create the five Reel variants with that footage and either the original audio or a new offline voiceover. The app never pretends to recognize shot semantics: the user decides what the extracted scene shows.

## Director v2 and narration

Six styles now use 7–9 short clips, detected letterbox removal with blurred real-footage fills, clear upper-third typography, and percussive sound accents. Pick the original soundtrack, a separately uploaded narration, or a locally synthesized voice. For better neural speech on an 8 GB CPU computer, install Piper and a correctly licensed voice model; Windows SAPI remains a basic fallback. The Reel Lab keeps the new sixth Voice Story format. No guaranteed social reach is claimed.

### Voice and music licensing

Before using a downloaded Piper voice commercially, read the model card for that exact voice and its training dataset license. Some otherwise high-quality models restrict commercial use. This repository does not bundle voice-model weights, third-party music or fonts. The separately generated six-Reel demo used a basic synthetic fallback where neural weights were unavailable; it is not a claim that the computer had Piper installed.

## One-time Windows neural voice setup (optional)

Double-click setup-ai-voice-windows.bat before starting the studio. It installs Piper in the local Python virtual environment and downloads one LibriTTS high-quality English voice and configuration to the ignored voices directory (about 137 MB). Then restart start-windows.bat; the launcher configures the model and female speaker 676 automatically. On an 8 GB CPU-only laptop, synthesis is local, with no API usage after installation.

Voice dataset: LibriTTS (OpenSLR 60), CC BY 4.0. Attribution should accompany commercial use; see the official model card at https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts/high/MODEL_CARD. The neural model is an optional download, not bundled in the repository or earlier demo videos.

### Speech compatibility and Reel Lab safeguard

The optional Piper installer and selected LibriTTS voice now use the current `python -m piper` CLI for synthesis. The configured speaker index is respected, and a legacy binary remains supported. Scene boundaries are cached per original clip during each render to reduce repeated CPU analysis, and the three soundtrack buttons are bound correctly in the browser. Unit/contract tests cover these paths.

## Optional VoiceStudio voice engine (2026)

EasyVideo can connect to the independent [VoiceStudio](https://github.com/debpalash/VoiceStudio) **running on your own PC**, using its OpenAI-compatible `/v1/audio/speech` REST endpoint at `http://127.0.0.1:3900`. Set `EASYVIDEO_VOICESTUDIO_MODEL=tts-1` (or a local installed engine such as KittenTTS) and `EASYVIDEO_VOICESTUDIO_VOICE=alloy` (or a voice profile). The studio lets you select **VoiceStudio local** for a narrated Reel when available. The connector only permits loopback HTTP with no redirects or proxy use. No account, GPU or paid API is required *by EasyVideo*, but you must separately install VoiceStudio and any chosen model, which may consume substantial RAM. For an 8 GB PC choose a lightweight CPU-compatible model such as KittenTTS, not a 1B+ parameter voice-cloning model. No VoiceStudio source has been copied; its AGPL license and each voice model's separate conditions still apply.

## Instagram discovery pack

For each generated style EasyVideo prepares a searchable headline, natural-language caption, simple hashtags, accessibility alt text, a pinned comment and a manual publishing checklist. Optional city/area comes **only from your campaign brief**, avoiding fabricated location targeting. Discovery depends on relevance and real audience response, not keyword stuffing. No automated posting or reach promises.

### Licensed stock vs real footage

For office-sales Reels, label commercially licensed B-roll as Illustrative stock and assign only the Office atmosphere role. Genuine company/product footage must supply Hero, Detail, Workspace, Inventory, Function and Customer proof roles. Stock office settings are never presented as Furnihub's own completed projects or available products. When two independent stock clips have been added along with real required shots, EasyVideo reports the stock benchmark ready. Both video variants still require human review and truthful copy.

## Silent-first sales Reels + office-chair SEO (October 2026)

The Reel Lab now defaults to **Music + captions**. This uses only original, locally synthesized music with no voice model needed. Existing AI voiceover, original Reel audio, and uploaded narration modes remain available. Marketing copy for office/procurement audiences now leads with office-chair search terms, actual footage, and a qualified call to action: **DM OFFICE + chair count**. Each Reel provides a cover title, natural-language description, accessibility alt text, and suggested pinned comment. Location keywords appear only when the service region is entered and verified. Voice is optional; writing accurate sales copy is not.
