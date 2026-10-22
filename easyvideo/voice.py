"""Local speech engines: Piper neural TTS, Windows SAPI, or eSpeak.

No API key. Piper voice assets are user-installed and have separate licences.
"""
from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


class VoiceUnavailable(RuntimeError):
    pass


def configured_piper_model() -> Path | None:
    explicit = os.environ.get("EASYVIDEO_PIPER_MODEL", "").strip()
    default = Path(__file__).resolve().parents[1] / "models" / "piper" / "en_US-ljspeech-medium.onnx"
    model = Path(explicit).expanduser() if explicit else default
    if model.is_file() and Path(str(model) + ".json").is_file():
        return model
    return None


def engines() -> list[str]:
    available: list[str] = []
    model = configured_piper_model()
    if model and (importlib.util.find_spec("piper") is not None or shutil.which("piper")):
        available.append("piper")
    if platform.system() == "Windows" and (shutil.which("powershell") or shutil.which("pwsh")):
        available.append("sapi")
    if shutil.which("espeak-ng"):
        available.append("espeak-ng")
    elif shutil.which("espeak"):
        available.append("espeak")
    return available


def synthesize(text: str, output: Path, preferred: str = "auto") -> str:
    options = engines()
    if not options:
        raise VoiceUnavailable(
            "No local voice engine. Install Piper using setup-voice-windows.bat "
            "or use a Windows SAPI/eSpeak voice."
        )
    engine = options[0] if preferred == "auto" else preferred
    if engine not in options:
        raise VoiceUnavailable(f"Voice '{engine}' unavailable; found {', '.join(options)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip()[:1200]
    if not text:
        raise VoiceUnavailable("Voiceover script is empty.")
    if engine == "piper":
        model = configured_piper_model()
        if not model:
            raise VoiceUnavailable("Piper model and matching ONNX JSON are missing.")
        if importlib.util.find_spec("piper") is not None:
            cmd = [sys.executable, "-m", "piper", "-m", str(model.resolve()),
                   "-f", str(output.resolve()), "--", text]
            subprocess.run(cmd, check=True, capture_output=True, timeout=150)
        else:
            # Compatibility with older standalone Piper binaries.
            cmd = ["piper", "--model", str(model.resolve()), "--output_file", str(output.resolve())]
            subprocess.run(cmd, input=text.encode("utf-8"), check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=150)
    elif engine == "sapi":
        destination = str(output.resolve()).replace("'", "''")
        safe_text = text.replace("'", "''")
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$v=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$v.SetOutputToWaveFile('{destination}');$v.Speak('{safe_text}');$v.Dispose()"
        )
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        subprocess.run([shutil.which("powershell") or "pwsh", "-NoProfile",
                        "-EncodedCommand", encoded], check=True, capture_output=True, timeout=120)
    else:
        subprocess.run([engine, "-w", str(output), "-s", "158", text], check=True,
                       capture_output=True, timeout=120)
    if not output.is_file() or output.stat().st_size < 100:
        raise VoiceUnavailable(f"{engine} produced no narration audio")
    return engine
