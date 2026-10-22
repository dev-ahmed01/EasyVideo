"""Offline speech: modern Piper neural TTS, Windows SAPI, or eSpeak fallback."""
from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
from . import voicestudio_bridge
import platform
import shutil
import subprocess
import sys


class VoiceUnavailable(RuntimeError):
    pass


def _piper_model() -> Path | None:
    raw = os.environ.get("EASYVIDEO_PIPER_MODEL", "").strip()
    if not raw:
        return None
    model = Path(raw).expanduser()
    return model if model.is_file() and Path(str(model) + ".json").is_file() else None


def _modern_piper_installed() -> bool:
    try:
        return importlib.util.find_spec("piper") is not None
    except (ImportError, ValueError):
        return False


def engines() -> list[str]:
    found: list[str] = []
    if _piper_model() and (_modern_piper_installed() or shutil.which("piper")):
        found.append("piper")
    if platform.system() == "Windows" and (shutil.which("powershell") or shutil.which("pwsh")):
        found.append("sapi")
    if shutil.which("espeak-ng"):
        found.append("espeak-ng")
    elif shutil.which("espeak"):
        found.append("espeak")
    if voicestudio_bridge.available():
        found.append("voicestudio")
    return found


def synthesize(text: str, output: Path, preferred: str = "auto") -> str:
    available = engines()
    if not available:
        raise VoiceUnavailable(
            "No offline voice is configured. Run setup-ai-voice-windows.bat "
            "or enable Windows SAPI/eSpeak."
        )
    engine = available[0] if preferred == "auto" else preferred
    if engine not in available:
        raise VoiceUnavailable(f"Voice engine '{engine}' unavailable. Available: {', '.join(available)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip()[:1200]
    if not text:
        raise VoiceUnavailable("Voiceover script is empty.")
    if engine == "voicestudio":
        return voicestudio_bridge.synthesize(text, output)
    if engine == "piper":
        model = _piper_model()
        if not model:
            raise VoiceUnavailable("Piper model and its matching JSON configuration are missing.")
        speaker = os.environ.get("EASYVIDEO_PIPER_SPEAKER", "").strip()
        if _modern_piper_installed():
            # OHF Piper 1.8+ uses: python -m piper -m MODEL -f OUTPUT [--speaker N] -- TEXT
            command = [sys.executable, "-m", "piper", "-m", str(model.resolve()),
                       "-f", str(output.resolve())]
            if speaker.isdigit():
                command.extend(["--speaker", speaker])
            command.extend(["--", text])
            subprocess.run(command, check=True, capture_output=True, timeout=180)
        else:
            # Legacy CLI compatibility for older standalone binaries.
            command = ["piper", "--model", str(model.resolve()), "--output_file", str(output.resolve())]
            if speaker.isdigit():
                command.extend(["--speaker", speaker])
            subprocess.run(command, input=text.encode("utf-8"), check=True, timeout=180,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif engine == "sapi":
        path = str(output.resolve()).replace("'", "''")
        safe_text = text.replace("'", "''")
        script = ("Add-Type -AssemblyName System.Speech; "
                  "$v=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  f"$v.SetOutputToWaveFile('{path}');$v.Speak('{safe_text}');$v.Dispose()")
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        subprocess.run([shutil.which("powershell") or "pwsh", "-NoProfile",
                        "-EncodedCommand", encoded], check=True, capture_output=True, timeout=120)
    else:
        subprocess.run([engine, "-w", str(output), "-s", "158", text], check=True,
                       capture_output=True, timeout=120)
    if not output.is_file() or output.stat().st_size < 100:
        raise VoiceUnavailable(f"{engine} produced no voiceover")
    return engine
