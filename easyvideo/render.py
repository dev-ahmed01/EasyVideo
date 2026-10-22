"""Memory-limited sequential FFmpeg Reel rendering with original-footage edits."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import wave
from typing import Callable

from .creative import Brief, STYLES, creatives
from .voice import synthesize

def _run(args: list[str], timeout: int = 180) -> None:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"FFmpeg failed: {p.stderr[-1700:]}")

def probe(path: Path) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                         "format=duration:stream=codec_type,width,height",
                         "-of", "json", str(path)], capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise ValueError("This clip could not be read by FFprobe.")
    info = json.loads(p.stdout)
    video = next((x for x in info.get("streams", []) if x.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("The uploaded file has no video stream.")
    return {"duration": float(info.get("format", {}).get("duration") or 0),
            "width": int(video.get("width", 0)),
            "height": int(video.get("height", 0))}

def _font() -> Path | None:
    env = os.getenv("EASYVIDEO_FONT")
    candidates = [Path(env)] if env else []
    candidates += [Path("C:/Windows/Fonts/arialbd.ttf"),
                   Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                   Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")]
    return next((x for x in candidates if x.is_file()), None)

def _escape_filter_path(path: Path) -> str:
    # FFmpeg filter parsers treat ":" and "\" specially; quote each pass.
    val = path.resolve().as_posix().replace("\\", "\\\\").replace(":", "\\:")
    val = val.replace("'", "\\'")
    return val

def _drawtext(text_path: Path, font_size: int, text_color: str, y: str) -> str:
    options = f"textfile='{_escape_filter_path(text_path)}':reload=0"
    font = _font()
    if font:
        options = f"fontfile='{_escape_filter_path(font)}':" + options
    return f"drawtext={options}:fontcolor={text_color}:fontsize={font_size}:x=(w-text_w)/2:y={y}:shadowcolor=black@0.65:shadowx=2:shadowy=3"

def _effects(style: str, idx: int, width: int, height: int, duration: float, text_path: Path) -> str:
    base = (f"fps=24,scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,format=yuv420p,"
            "eq=contrast=1.04:saturation=1.08")
    # Typography and rhythm vary by format; all filters are CPU-only.
    # Keep added titles at the top: source Reels can already contain lower thirds.
    if style == "stomp":
        size, y, opacity, color = 58, "h*0.17+68*exp(-14*t)", "0.57", "0xd6f39b"
    elif style == "cinematic":
        size, y, opacity, color = 41, "h*0.18+22*exp(-2*t)", "0.37", "0xf5e8d2"
    elif style == "features":
        size, y, opacity, color = 45, "h*0.17+25*exp(-9*t)", "0.46", "0x9fe5d7"
    elif style == "business":
        size, y, opacity, color = 43, "h*0.17+28*exp(-6*t)", "0.44", "0xf4dfa5"
    else:
        size, y, opacity, color = 50, "h*0.16+43*exp(-13*t)", "0.45", "0xf2c6e9"
    size = max(24, round(size * width / 540))
    base += f",drawbox=x=0:y=ih*0.07:w=iw:h=ih*0.29:color=black@{opacity}:t=fill"
    if style == "stomp":
        base += ",drawbox=x=0:y=ih*0.37:w=iw:h=7:color=0xd5ff56@0.9:t=fill"
    elif style == "features":
        base += ",drawbox=x=iw*0.07:y=ih*0.36:w=iw*0.14:h=5:color=0x8fe0da@0.9:t=fill"
    elif style == "business":
        base += ",drawbox=x=iw*0.07:y=ih*0.36:w=iw*0.14:h=5:color=0xe3b873@0.9:t=fill"
    base += "," + _drawtext(text_path, size, color, y)
    if style == "cinematic":
        base += f",fade=t=in:st=0:d=0.23,fade=t=out:st={max(0.2, duration-0.2):.2f}:d=0.2"
    return base

def _sfx(path: Path, duration: float, beats: list[float], style: str) -> None:
    # Self-generated percussive pulses. No copyrighted downloaded music.
    rate = 16000
    n = int(duration * rate)
    pulses = [0.0] * n
    rng = random.Random(42)
    gain = 0.25 if style == "stomp" else 0.08
    for beat in beats:
        offset = int(beat * rate)
        length = min(int(0.16 * rate), n - offset)
        for i in range(max(0, length)):
            t = i / rate
            sample = math.sin(2 * math.pi * 85 * t) * math.exp(-28*t)
            sample += (rng.random()*2-1) * 0.13 * math.exp(-38*t)
            pulses[offset+i] += gain * sample
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        import array
        chunk = array.array("h", [max(-32768, min(32767, int(x*32767))) for x in pulses])
        f.writeframes(chunk.tobytes())

def _clip_for(role: str, clips: list[dict], used: dict[str, int]) -> dict:
    choices = [x for x in clips if x["role"] == role and x["duration"] >= 1]
    if not choices:
        choices = [x for x in clips if x["role"] == "hero"] or clips
    index = used.get(role, 0)
    used[role] = index + 1
    return choices[index % len(choices)]

def render_variant(brief: Brief, clips: list[dict], style: str, project_dir: Path,
                   resolution: str = "preview", voice_engine: str = "auto",
                   progress: Callable[[str], None] | None = None,
                   reference_video: Path | None = None,
                   reference_start: float = 0,
                   reference_seconds: float = 18) -> Path:
    if style not in STYLES:
        raise ValueError(f"Unknown style: {style}")
    if resolution not in ("preview", "final"):
        raise ValueError("Invalid resolution")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe must be installed and available on PATH.")
    if not clips:
        raise ValueError("Please upload footage before rendering")
    width, height = (540, 960) if resolution == "preview" else (1080, 1920)
    plan = next(x for x in creatives(brief) if x["id"] == style)
    base_seconds = STYLES[style]["seconds"]
    work = project_dir / "work" / f"{style}_{resolution}"
    work.mkdir(parents=True, exist_ok=True)
    voice_path = work / "voice.wav"
    if reference_video is not None:
        if progress: progress("Bringing in audio from the existing Reel")
        _run(["ffmpeg", "-y", "-v", "error", "-ss", str(reference_start),
              "-i", str(reference_video), "-t", str(reference_seconds),
              "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a",
              "pcm_s16le", str(voice_path)], timeout=120)
        engine = "original Reel audio"
    else:
        if progress: progress("Generating offline voiceover")
        engine = synthesize(plan["voiceover"], voice_path, preferred=voice_engine)
    voice_seconds = probe_audio(voice_path)
    target = max(sum(base_seconds), voice_seconds + 0.9)
    # Narration is never silently cut short. A long user script can yield a longer reel.
    multiplier = target / sum(base_seconds)
    seconds = [round(s * multiplier, 3) for s in base_seconds]
    segments: list[Path] = []
    elapsed = 0.0
    beats = []
    used: dict[str, int] = {}
    for idx, (role, duration, text) in enumerate(zip(plan["roles"], seconds, plan["beats"])):
        clip = _clip_for(role, clips, used)
        original = project_dir / "clips" / clip["stored_name"]
        if not original.is_file():
            raise RuntimeError(f"Source clip not found: {clip['filename']}")
        overlay = work / f"beat_{idx}.txt"
        overlay.write_text(text, encoding="utf-8")
        segment = work / f"segment_{idx:02d}.mp4"
        start = min(max(0, clip["duration"] - duration), clip["duration"] * ((idx % 3) * 0.16))
        # Loop the source to cover shots shorter than a requested scene; no blank frames.
        vf = _effects(style, idx, width, height, duration, overlay)
        _run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1",
              "-ss", str(round(start, 2)), "-i", str(original),
              "-t", str(duration), "-an", "-vf", vf,
              "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
              "-pix_fmt", "yuv420p", "-r", "24", "-threads", "2", str(segment)], timeout=240)
        beats.append(elapsed)
        elapsed += duration
        segments.append(segment)
        if progress: progress(f"Rendering {style}: scene {idx+1}/4")
    manifest = work / "concat.txt"
    # ffmpeg concat demuxer requires escaped absolute paths.
    manifest.write_text("\n".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'" for p in segments), encoding="utf-8")
    silent = work / "silent.mp4"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(silent)])
    sound = work / "pulses.wav"
    _sfx(sound, elapsed, beats, style)
    final_dir = project_dir / "exports"
    final_dir.mkdir(exist_ok=True)
    out = final_dir / f"{style}_{resolution}.mp4"
    if progress: progress(f"Mixing narration and sound for {style}")
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(voice_path),
          "-i", str(sound), "-filter_complex",
          "[1:a]volume=1.0[vo];[2:a]volume=0.65[fx];[vo][fx]amix=inputs=2:duration=longest:dropout_transition=0[a]",
          "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
          "-b:a", "128k", "-t", str(elapsed), "-movflags", "+faststart",
          str(out)], timeout=120)
    if progress: progress(f"{plan['title']} {resolution} complete ({engine} voice)")
    return out

def probe_audio(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True, timeout=15, check=True)
    return float(p.stdout.strip())
