"""Full path: marketing brief -> upload -> coverage audit -> CPU render -> download."""
import io
import math
import shutil
import struct
import subprocess
import wave

import pytest
from fastapi.testclient import TestClient

from easyvideo.server import create_app
from easyvideo import render


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg required for true media integration test")
def test_from_brief_to_downloadable_reel(tmp_path, monkeypatch):
    original = tmp_path / "sample.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=gray:s=540x960:r=24", "-t", "2.5",
                    "-c:v", "libx264", "-preset", "ultrafast", str(original)],
                   check=True, timeout=45)

    def voice(text, out, preferred="auto"):
        with wave.open(str(out), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            pcm = bytearray()
            for n in range(16000):
                pcm += struct.pack("<h", int(900 * math.sin(2 * math.pi * 210 * n / 16000)))
            wav.writeframes(bytes(pcm))
        return "synthetic-ci-voice"

    monkeypatch.setattr(render, "synthesize", voice)
    with TestClient(create_app(tmp_path / "data")) as client:
        brief = {"intent": "Show a comfortable desk chair and invite individual enquiries",
                 "product": "Mesh chair"}
        created = client.post("/api/projects", json=brief)
        assert created.status_code == 201
        pid = created.json()["id"]

        for role in ("hero", "detail"):
            upload = client.post(
                "/api/projects/" + pid + "/clips",
                data={"role": role},
                files={"file": (role + ".mp4", io.BytesIO(original.read_bytes()), "video/mp4")})
            assert upload.status_code == 201, upload.text

        assert client.get("/api/projects/" + pid).json()["audit"]["ready"]
        queued = client.post("/api/projects/" + pid + "/renders",
                             json={"styles": ["stomp"], "resolution": "preview"})
        assert queued.status_code == 202, queued.text
        project = client.get("/api/projects/" + pid).json()
        assert project["job"]["status"] == "ready", project["job"]
        assert "preview" in project["exports"]["stomp"]
        video = client.get(project["exports"]["stomp"]["preview"])
        assert video.status_code == 200
        assert video.headers["content-type"].startswith("video/mp4")
        assert len(video.content) > 20_000
