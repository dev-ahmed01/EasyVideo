"""Local-only FastAPI app. Explicit user clip labels, no cloud uploads."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import uuid

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
import subprocess

from .creative import Brief, ROLES, STYLES, audit, creatives, required_shots
from .render import probe, render_variant
from .voice import engines

HERE = Path(__file__).resolve().parent.parent
EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
MAX_UPLOAD = 250 * 1024 * 1024

class BriefInput(BaseModel):
    intent: str = Field(min_length=10, max_length=1400)
    audience: str = Field(default="Office and work-from-home buyers", max_length=180)
    product: str = Field(default="Office chair", max_length=120)
    offer: str = Field(default="", max_length=400)
    facts: str = Field(default="", max_length=450)
    call_to_action: str = Field(default="DM us for availability", max_length=180)
    script: str = Field(default="", max_length=1800)
    source_mode: Literal["new", "remix"] = "new"
    brand_name: str = Field(default="", max_length=90)

class RenderInput(BaseModel):
    styles: list[str] = Field(min_length=1, max_length=6)
    resolution: str = "preview"
    voice_engine: str = "auto"
    audio_source: Literal["generated", "reference", "uploaded"] = "generated"
    reference_start: float = Field(default=0, ge=0, le=600)
    reference_seconds: float = Field(default=18, ge=8, le=90)

class SelectionInput(BaseModel):
    styles: list[str] = Field(default_factory=list, max_length=3)

class ClipRoleInput(BaseModel):
    role: str

class ReferenceSegmentInput(BaseModel):
    role: str
    start: float = Field(ge=0, le=600)
    duration: float = Field(ge=2, le=60)

class PerformanceInput(BaseModel):
    post_url: str = Field(default="", max_length=500)
    views: int = Field(default=0, ge=0)
    reach: int = Field(default=0, ge=0)
    avg_watch_seconds: float = Field(default=0, ge=0, le=3600)
    shares: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    enquiries: int = Field(default=0, ge=0)

def create_app(data_dir: str | Path | None = None) -> FastAPI:
    root = Path(data_dir or os.getenv("EASYVIDEO_DATA_DIR", HERE / "easyvideo-data")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "projects.sqlite3"
    render_lock = threading.Lock()

    @contextmanager
    def db():
        cx = sqlite3.connect(db_path, timeout=30)
        cx.row_factory = sqlite3.Row
        try:
            yield cx
            cx.commit()
        finally:
            cx.close()

    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, brief TEXT NOT NULL,
            job_status TEXT NOT NULL DEFAULT 'idle',
            job_message TEXT NOT NULL DEFAULT '', selected TEXT NOT NULL DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS clips (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, filename TEXT NOT NULL,
            stored_name TEXT NOT NULL, role TEXT NOT NULL, width INTEGER NOT NULL,
            height INTEGER NOT NULL, duration REAL NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id));
        CREATE TABLE IF NOT EXISTS uploaded_narrations (
            project_id TEXT PRIMARY KEY, filename TEXT NOT NULL, duration REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS reference_reels (
            project_id TEXT PRIMARY KEY, filename TEXT NOT NULL,
            stored_name TEXT NOT NULL, duration REAL NOT NULL,
            width INTEGER NOT NULL, height INTEGER NOT NULL,
            has_audio INTEGER NOT NULL, audio_seconds REAL NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id));
        CREATE TABLE IF NOT EXISTS performance (
            project_id TEXT NOT NULL, style TEXT NOT NULL,
            post_url TEXT NOT NULL DEFAULT '', views INTEGER NOT NULL DEFAULT 0,
            reach INTEGER NOT NULL DEFAULT 0, avg_watch_seconds REAL NOT NULL DEFAULT 0,
            shares INTEGER NOT NULL DEFAULT 0, saves INTEGER NOT NULL DEFAULT 0,
            enquiries INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
            PRIMARY KEY(project_id,style),
            FOREIGN KEY(project_id) REFERENCES projects(id));
        UPDATE projects SET job_status='error',job_message='Interrupted by application restart'
            WHERE job_status IN ('queued','running');
        """)
    app = FastAPI(title="EasyVideo", version="0.1.0",
                  description="Offline-first marketing-led Instagram Reel studio")
    app.mount("/assets", StaticFiles(directory=str(HERE / "web")), name="assets")

    def fetch_project(pid: str) -> dict:
        with db() as cx:
            p = cx.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
            if p is None:
                raise HTTPException(404, "Project not found")
            clips = [dict(x) for x in cx.execute(
                "SELECT * FROM clips WHERE project_id=? ORDER BY rowid", (pid,)).fetchall()]
            raw_reference = cx.execute(
                "SELECT * FROM reference_reels WHERE project_id=?", (pid,)).fetchone()
            narration_row = cx.execute("SELECT * FROM uploaded_narrations WHERE project_id=?", (pid,)).fetchone()
            narration = dict(narration_row) if narration_row else None
            if narration:
                narration["audio_url"] = f"/api/projects/{pid}/narration/audio"
            reference = dict(raw_reference) if raw_reference else None
            if reference:
                reference.pop("stored_name")
                reference["media_url"] = f"/api/projects/{pid}/reference/media"
                reference["audio_url"] = f"/api/projects/{pid}/reference/audio" if reference["has_audio"] else None
        with db() as cx:
            metrics = {
                row["style"]: {key: row[key] for key in row.keys() if key not in ("style", "project_id")}
                for row in cx.execute("SELECT * FROM performance WHERE project_id=?", (pid,))
            }
        brief_data = json.loads(p["brief"])
        brief = Brief(**brief_data)
        exports = {}
        for style in STYLES:
            exports[style] = {
                resolution: f"/api/projects/{pid}/exports/{style}/{resolution}"
                for resolution in ("preview", "final")
                if (root / pid / "exports" / f"{style}_{resolution}.mp4").is_file()
            }
        return {
            "id": pid, "created_at": p["created_at"], "brief": brief_data,
            "shotlist": required_shots(brief), "creatives": creatives(brief),
            "clips": clips, "audit": audit(brief, clips),
            "job": {"status": p["job_status"], "message": p["job_message"]},
            "selected": json.loads(p["selected"]), "exports": exports,
            "performance": metrics, "reference": reference, "narration": narration
        }

    def invalidate_exports(pid: str):
        folder = root / pid / "exports"
        if folder.is_dir():
            for output in folder.glob("*.mp4"):
                output.unlink(missing_ok=True)

    def update_status(pid: str, status: str, message: str):
        with db() as c:
            c.execute("UPDATE projects SET job_status=?,job_message=? WHERE id=?",
                      (status, message, pid))

    @app.get("/")
    def home():
        return FileResponse(HERE / "web" / "index.html")

    @app.get("/api/health")
    def health():
        return {"ok": True, "ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
                "voices": engines(), "local_only": True, "max_upload_mb": 250}

    @app.post("/api/plan")
    def plan(payload: BriefInput):
        brief = Brief(**payload.model_dump())
        return {"shotlist": required_shots(brief), "creatives": creatives(brief),
                "strategy": "Distinct hooks, pacing and editing approaches. Clip roles are user-confirmed; no invented product claims."}

    @app.post("/api/projects", status_code=201)
    def create_project(payload: BriefInput):
        pid = uuid.uuid4().hex
        (root / pid / "clips").mkdir(parents=True)
        with db() as cx:
            cx.execute("INSERT INTO projects(id,created_at,brief) VALUES(?,?,?)",
                       (pid, datetime.now(timezone.utc).isoformat(),
                        json.dumps(payload.model_dump())))
        return fetch_project(pid)

    @app.get("/api/projects")
    def list_projects():
        with db() as cx:
            rows = cx.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 30").fetchall()
        return [{"id": p["id"], "intent": fetch_project(p["id"])["brief"]["intent"],
                 "created_at": fetch_project(p["id"])["created_at"]} for p in rows]

    @app.get("/api/projects/{pid}")
    def project(pid: str):
        return fetch_project(pid)

    @app.post("/api/projects/{pid}/clips", status_code=201)
    async def upload_clip(pid: str, file: UploadFile = File(...), role: str = Form(...)):
        fetch_project(pid)
        if role not in ROLES:
            raise HTTPException(422, "Select a valid shot role")
        name = Path(file.filename or "clip").name
        ext = Path(name).suffix.lower()
        if ext not in EXTENSIONS:
            raise HTTPException(415, "Upload an MP4, MOV, M4V, MKV or WebM video")
        cid = uuid.uuid4().hex
        stored = f"{cid}{ext}"
        dest = root / pid / "clips" / stored
        size = 0
        try:
            with dest.open("wb") as dst:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, "Clip exceeds 250 MB limit")
                    dst.write(chunk)
            if size == 0:
                raise HTTPException(422, "Clip is empty")
            try:
                info = probe(dest)
            except (ValueError, OSError, RuntimeError) as err:
                raise HTTPException(422, str(err)) from err
            if info["duration"] < 1 or info["duration"] > 1200:
                raise HTTPException(422, "Clip must be between 1 second and 20 minutes")
            with db() as cx:
                cx.execute("INSERT INTO clips VALUES(?,?,?,?,?,?,?,?)",
                           (cid, pid, name[:160], stored, role, info["width"],
                            info["height"], info["duration"]))
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        invalidate_exports(pid)
        return fetch_project(pid)

    @app.patch("/api/projects/{pid}/clips/{cid}")
    def relabel_clip(pid: str, cid: str, payload: ClipRoleInput):
        fetch_project(pid)
        if payload.role not in ROLES:
            raise HTTPException(422, "Invalid shot role")
        with db() as cx:
            cur = cx.execute("UPDATE clips SET role=? WHERE project_id=? AND id=?",
                             (payload.role, pid, cid))
            if cur.rowcount != 1:
                raise HTTPException(404, "Clip not found")
        invalidate_exports(pid)
        return fetch_project(pid)

    @app.delete("/api/projects/{pid}/clips/{cid}")
    def delete_clip(pid: str, cid: str):
        fetch_project(pid)
        with db() as cx:
            row = cx.execute("SELECT stored_name FROM clips WHERE id=? AND project_id=?",
                             (cid, pid)).fetchone()
            if not row:
                raise HTTPException(404, "Clip not found")
            cx.execute("DELETE FROM clips WHERE id=? AND project_id=?", (cid, pid))
        (root / pid / "clips" / row["stored_name"]).unlink(missing_ok=True)
        invalidate_exports(pid)
        return fetch_project(pid)

    @app.get("/api/projects/{pid}/clips/{cid}/media")
    def preview_uploaded_clip(pid: str, cid: str):
        fetch_project(pid)
        with db() as cx:
            row = cx.execute("SELECT stored_name FROM clips WHERE id=? AND project_id=?", (cid, pid)).fetchone()
            if row is None:
                raise HTTPException(404, "Clip not found")
        target = root / pid / "clips" / row["stored_name"]
        if not target.is_file():
            raise HTTPException(404, "Source file missing")
        return FileResponse(target, media_type="video/mp4")

    def reference_file(pid: str) -> Path:
        with db() as cx:
            row = cx.execute("SELECT stored_name FROM reference_reels WHERE project_id=?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404, "No original Reel uploaded")
        target = root / pid / "references" / row["stored_name"]
        if not target.is_file():
            raise HTTPException(404, "Original Reel file missing")
        return target

    @app.post("/api/projects/{pid}/reference", status_code=201)
    async def add_reference(pid: str, file: UploadFile = File(...)):
        """Store the original Reel once; never call an external service."""
        fetch_project(pid)
        if render_lock.locked():
            raise HTTPException(409, "Finish rendering before changing source footage")
        name = Path(file.filename or "reel").name
        ext = Path(name).suffix.lower()
        if ext not in EXTENSIONS:
            raise HTTPException(415, "Select a video file")
        (root / pid / "references").mkdir(parents=True, exist_ok=True)
        stored = f"{uuid.uuid4().hex}{ext}"
        dest = root / pid / "references" / stored
        size = 0
        try:
            with dest.open("wb") as output:
                while part := await file.read(1024 * 1024):
                    size += len(part)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, "Original Reel exceeds 250 MB")
                    output.write(part)
            if size == 0:
                raise HTTPException(422, "Original Reel is empty")
            info = probe(dest)
            if info["duration"] < 1 or info["duration"] > 600:
                raise HTTPException(422, "Original Reel must be between 1 second and 10 minutes")
            audio_check = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=codec_name,duration", "-of", "json", str(dest)],
                capture_output=True, text=True, timeout=20, check=True
            )
            streams = json.loads(audio_check.stdout).get("streams", [])
            has_audio = bool(streams)
            audio_seconds = float(streams[0].get("duration") or info["duration"]) if has_audio else 0.0
            with db() as cx:
                old = cx.execute(
                    "SELECT stored_name FROM reference_reels WHERE project_id=?", (pid,)
                ).fetchone()
                cx.execute(
                    """INSERT INTO reference_reels(
                        project_id,filename,stored_name,duration,width,height,has_audio,audio_seconds
                    ) VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(project_id) DO UPDATE SET
                    filename=excluded.filename, stored_name=excluded.stored_name,
                    duration=excluded.duration, width=excluded.width,
                    height=excluded.height, has_audio=excluded.has_audio,
                    audio_seconds=excluded.audio_seconds""",
                    (pid, name[:160], stored, info["duration"], info["width"],
                     info["height"], int(has_audio), audio_seconds)
                )
            if old:
                (root / pid / "references" / old["stored_name"]).unlink(missing_ok=True)
            # Replacing a reference invalidates videos rendered with its older audio.
            for rendered in (root / pid / "exports").glob("*.mp4") if (root / pid / "exports").is_dir() else []:
                rendered.unlink(missing_ok=True)
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        return fetch_project(pid)

    @app.get("/api/projects/{pid}/reference/media")
    def view_reference(pid: str):
        target = reference_file(pid)
        return FileResponse(target, media_type={
            ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"
        }.get(target.suffix.lower(), "application/octet-stream"))

    @app.get("/api/projects/{pid}/reference/audio")
    def hear_reference(pid: str):
        target = reference_file(pid)
        project = fetch_project(pid)
        if not project["reference"]["has_audio"]:
            raise HTTPException(409, "This Reel has no audio track")
        audio = root / pid / "references" / "extracted_audio.m4a"
        if not audio.is_file() or audio.stat().st_mtime < target.stat().st_mtime:
            command = ["ffmpeg", "-y", "-v", "error", "-i", str(target),
                       "-vn", "-map", "0:a:0", "-c:a", "aac", "-b:a", "112k",
                       str(audio)]
            p = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if p.returncode:
                raise HTTPException(422, "Couldn't extract the original audio")
        return FileResponse(audio, media_type="audio/mp4")

    @app.post("/api/projects/{pid}/reference/segments", status_code=201)
    def import_reference_segment(pid: str, payload: ReferenceSegmentInput):
        """Pick a time range of the previous Reel as an editable shot.
        The user labels the visual subject; the application does not invent it.
        """
        project = fetch_project(pid)
        if payload.role not in ROLES:
            raise HTTPException(422, "Select a valid shot role")
        if not project["reference"]:
            raise HTTPException(409, "Upload your original Reel first")
        if payload.start + payload.duration > project["reference"]["duration"] + 0.03:
            raise HTTPException(422, "Selected time range exceeds original video")
        if render_lock.locked():
            raise HTTPException(409, "Finish rendering before changing footage")
        original = reference_file(pid)
        cid = uuid.uuid4().hex
        stored = f"{cid}.mp4"
        dest = root / pid / "clips" / stored
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-ss", str(payload.start),
            "-i", str(original), "-t", str(payload.duration), "-map", "0:v:0",
            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
            "-threads", "2", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(dest)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise HTTPException(422, "Unable to cut this part of the Reel")
            info = probe(dest)
            if info["duration"] < 1:
                raise HTTPException(422, "Could not extract a usable shot")
            display = f"Original Reel {payload.start:.1f}s–{payload.start + payload.duration:.1f}s"
            with db() as cx:
                cx.execute("INSERT INTO clips VALUES(?,?,?,?,?,?,?,?)",
                           (cid, pid, display, stored, payload.role,
                            info["width"], info["height"], info["duration"]))
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        invalidate_exports(pid)
        return fetch_project(pid)

    @app.post("/api/projects/{pid}/narration", status_code=201)
    async def upload_narration(pid: str, file: UploadFile = File(...)):
        fetch_project(pid)
        if render_lock.locked():
            raise HTTPException(409, "Finish rendering before changing narration")
        name = Path(file.filename or "narration").name
        ext = Path(name).suffix.lower()
        if ext not in {".wav", ".mp3", ".m4a", ".aac", ".ogg"}:
            raise HTTPException(415, "Choose WAV, MP3, M4A, AAC or OGG")
        folder = root / pid / "narration"
        folder.mkdir(parents=True, exist_ok=True)
        raw = folder / f"raw_{uuid.uuid4().hex}{ext}"
        temp = folder / f"converted_{uuid.uuid4().hex}.wav"
        output = folder / "voice.wav"
        size = 0
        try:
            with raw.open("wb") as dest:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 25 * 1024 * 1024:
                        raise HTTPException(413, "Audio exceeds 25 MB")
                    dest.write(chunk)
            p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw),
                "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(temp)],
                capture_output=True, text=True, timeout=120)
            if p.returncode:
                raise HTTPException(422, "No usable audio was found")
            p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(temp)],
                capture_output=True, text=True, timeout=15, check=True)
            duration = float(p.stdout.strip())
            if not 2 <= duration <= 180:
                raise HTTPException(422, "Narration must be 2–180 seconds")
            temp.replace(output)
            with db() as cx:
                cx.execute("""INSERT INTO uploaded_narrations(project_id,filename,duration)
                    VALUES(?,?,?) ON CONFLICT(project_id) DO UPDATE SET
                    filename=excluded.filename, duration=excluded.duration""",
                    (pid, name[:160], duration))
        finally:
            raw.unlink(missing_ok=True)
            temp.unlink(missing_ok=True)
            await file.close()
        invalidate_exports(pid)
        return fetch_project(pid)

    @app.get("/api/projects/{pid}/narration/audio")
    def narration_audio(pid: str):
        p = fetch_project(pid)
        if not p["narration"]:
            raise HTTPException(404, "No narration")
        path = root / pid / "narration" / "voice.wav"
        if not path.is_file():
            raise HTTPException(404, "Narration file unavailable")
        return FileResponse(path, media_type="audio/wav")

    def render_job(pid: str, styles: list[str], resolution: str, voice_engine: str,
                   audio_source: str, reference_start: float, reference_seconds: float):
        try:
            update_status(pid, "running", "Starting the render queue")
            data = fetch_project(pid)
            brief = Brief(**data["brief"])
            for index, style in enumerate(styles):
                def show(message: str, i=index):
                    update_status(pid, "running", f"{i+1}/{len(styles)} · {message}")
                reference_path = reference_file(pid) if audio_source == "reference" else None
                narration_file = root / pid / "narration" / "voice.wav" if audio_source == "uploaded" else None
                render_variant(brief, data["clips"], style, root / pid, resolution,
                               voice_engine, progress=show, reference_video=reference_path,
                               reference_start=reference_start,
                               reference_seconds=reference_seconds, voiceover_file=narration_file)
            update_status(pid, "ready", f"{len(styles)} {resolution} Reel(s) ready")
        except Exception as exc:
            update_status(pid, "error", str(exc)[:1000])
        finally:
            render_lock.release()

    @app.post("/api/projects/{pid}/renders", status_code=202)
    def start_render(pid: str, payload: RenderInput, background: BackgroundTasks):
        data = fetch_project(pid)
        if not data["audit"]["ready"]:
            raise HTTPException(409, "Missing required shots: " +
                                ", ".join(x["label"] for x in data["audit"]["missing"]))
        if payload.resolution not in ("preview", "final"):
            raise HTTPException(422, "Invalid resolution")
        if len(set(payload.styles)) != len(payload.styles) or any(x not in STYLES for x in payload.styles):
            raise HTTPException(422, "Choose unique valid Reel styles")
        if payload.audio_source == "reference":
            if not data["reference"] or not data["reference"]["has_audio"]:
                raise HTTPException(409, "Upload an existing Reel that contains audio first")
            if payload.reference_start + payload.reference_seconds > data["reference"]["audio_seconds"] + 0.1:
                raise HTTPException(422, "Selected original audio range exceeds available audio")
        elif payload.audio_source == "uploaded":
            if not data["narration"] or not (root / pid / "narration" / "voice.wav").is_file():
                raise HTTPException(409, "Upload narration first")
        else:
            if payload.voice_engine != "auto" and payload.voice_engine not in engines():
                raise HTTPException(422, "Voice provider is unavailable")
            if not engines():
                raise HTTPException(409, "Install Piper, or use Windows SAPI / eSpeak for offline voiceovers.")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise HTTPException(409, "FFmpeg and FFprobe are required.")
        if not render_lock.acquire(blocking=False):
            raise HTTPException(409, "A video render is already running")
        try:
            update_status(pid, "queued", f"Queued {len(payload.styles)} styles")
            background.add_task(render_job, pid, payload.styles, payload.resolution,
                                payload.voice_engine, payload.audio_source,
                                payload.reference_start, payload.reference_seconds)
        except Exception:
            render_lock.release()
            raise
        return {"status": "queued", "styles": payload.styles,
                "resolution": payload.resolution, "audio_source": payload.audio_source}

    @app.post("/api/projects/{pid}/selection")
    def select(pid: str, payload: SelectionInput):
        fetch_project(pid)
        if len(set(payload.styles)) != len(payload.styles) or any(x not in STYLES for x in payload.styles):
            raise HTTPException(422, "Choose up to three unique valid Reel styles")
        with db() as cx:
            cx.execute("UPDATE projects SET selected=? WHERE id=?",
                       (json.dumps(payload.styles), pid))
        return fetch_project(pid)

    @app.put("/api/projects/{pid}/performance/{style}")
    def save_performance(pid: str, style: str, payload: PerformanceInput):
        fetch_project(pid)
        if style not in STYLES:
            raise HTTPException(404, "Unknown creative format")
        data = payload.model_dump()
        with db() as cx:
            cx.execute("""INSERT INTO performance(
                project_id, style, post_url, views, reach, avg_watch_seconds,
                shares, saves, enquiries, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(project_id,style) DO UPDATE SET
                post_url=excluded.post_url, views=excluded.views,
                reach=excluded.reach, avg_watch_seconds=excluded.avg_watch_seconds,
                shares=excluded.shares, saves=excluded.saves,
                enquiries=excluded.enquiries, updated_at=excluded.updated_at""",
                (pid, style, data["post_url"], data["views"], data["reach"],
                 data["avg_watch_seconds"], data["shares"], data["saves"],
                 data["enquiries"], datetime.now(timezone.utc).isoformat()))
        return fetch_project(pid)

    @app.get("/api/projects/{pid}/exports/{style}/{resolution}")
    def download(pid: str, style: str, resolution: str):
        fetch_project(pid)
        if style not in STYLES or resolution not in ("preview", "final"):
            raise HTTPException(404, "Export not found")
        path = root / pid / "exports" / f"{style}_{resolution}.mp4"
        if not path.is_file():
            raise HTTPException(404, "Export not generated yet")
        return FileResponse(path, media_type="video/mp4", filename=path.name)

    return app

app = create_app()
