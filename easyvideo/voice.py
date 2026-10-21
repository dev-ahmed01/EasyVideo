"""Offline voiceover: Piper when configured; Windows SAPI or eSpeak fallback."""
from __future__ import annotations

import base64
import os
from pathlib import Path
import platform
import shutil
import subprocess

class VoiceUnavailable(RuntimeError):
    pass

def engines() -> list[str]:
    found = []
    model = os.getenv("EASYVIDEO_PIPER_MODEL", "")
    if shutil.which("piper") and model and Path(model).is_file():
        found.append("piper")
    if platform.system() == "Windows" and (shutil.which("powershell") or shutil.which("pwsh")):
        found.append("sapi")
    if shutil.which("espeak-ng"):
        found.append("espeak-ng")
    elif shutil.which("espeak"):
        found.append("espeak")
    return found

def synthesize(text: str, output: Path, preferred: str = "auto") -> str:
    available = engines()
    if not available:
        raise VoiceUnavailable("No offline voice engine found. On Windows enable Windows SAPI, or install Piper and configure EASYVIDEO_PIPER_MODEL.")
    engine = available[0] if preferred == "auto" else preferred
    if engine not in available:
        raise VoiceUnavailable(f"Voice engine '{engine}' unavailable. Available: {', '.join(available)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip()[:1200]
    if not text:
        raise VoiceUnavailable("Voiceover script is empty.")
    if engine == "piper":
        cmd = ["piper", "--model", os.environ["EASYVIDEO_PIPER_MODEL"],
               "--output_file", str(output)]
        subprocess.run(cmd, input=text.encode("utf-8"), check=True, timeout=120,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif engine == "sapi":
        out = str(output).replace("'", "''")
        safe_text = text.replace("'", "''")
        command = ("Add-Type -AssemblyName System.Speech; "
                   "$v=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                   f"$v.SetOutputToWaveFile('{out}');$v.Speak('{safe_text}');$v.Dispose()")
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        subprocess.run([shutil.which("powershell") or "pwsh", "-NoProfile",
                        "-EncodedCommand", encoded], check=True, timeout=120,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        subprocess.run([engine, "-w", str(output), "-s", "158", text],
                       check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not output.is_file() or output.stat().st_size < 100:
        raise VoiceUnavailable(f"{engine} produced no voiceover audio")
    return engine
