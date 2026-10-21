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

class RenderInput(BaseModel):
    styles: list[str] = Field(min_length=1, max_length=5)
    resolution: str = "preview"
    voice_engine: str = "auto"

class SelectionInput(BaseModel):
    styles: list[str] = Field(default_factory=list, max_length=3)

class ClipRoleInput(BaseModel):
    role: str

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
            "selected": json.loads(p["selected"]), "exports": exports, "performance": metrics
        }

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
        return fetch_project(pid)

    def render_job(pid: str, styles: list[str], resolution: str, voice_engine: str):
        try:
            update_status(pid, "running", "Starting the render queue")
            data = fetch_project(pid)
            brief = Brief(**data["brief"])
            for index, style in enumerate(styles):
                def show(message: str, i=index):
                    update_status(pid, "running", f"{i+1}/{len(styles)} · {message}")
                render_variant(brief, data["clips"], style, root / pid, resolution,
                               voice_engine, progress=show)
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
            background.add_task(render_job, pid, payload.styles, payload.resolution, payload.voice_engine)
        except Exception:
            render_lock.release()
            raise
        return {"status": "queued", "styles": payload.styles, "resolution": payload.resolution}

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
