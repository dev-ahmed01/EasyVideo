"""A real reference Reel supplies narration or full original soundtrack."""
import io
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from easyvideo.server import create_app
from easyvideo import render

pytestmark=pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg required for real media test"
)

def video_with_audio(tmp_path, with_audio=True):
    output=tmp_path/("audio.mp4" if with_audio else "silent.mp4")
    args=["ffmpeg","-y","-v","error","-f","lavfi","-i",
          "color=c=gray:s=360x640:r=24"]
    if with_audio:args+=["-f","lavfi","-i","sine=frequency=330:sample_rate=16000"]
    args+=["-t","9","-c:v","libx264","-preset","ultrafast"]
    if with_audio:args+=["-c:a","aac","-shortest"]
    subprocess.run(args+[str(output)],check=True,timeout=50)
    return output.read_bytes()

def test_reference_audio_remix_end_to_end(tmp_path,monkeypatch):
    movie=video_with_audio(tmp_path)
    def no_tts(*args,**kwargs):
        raise AssertionError("Should use original Reel audio, not TTS")
    monkeypatch.setattr(render,"synthesize",no_tts)
    with TestClient(create_app(tmp_path/"store")) as client:
        payload={"source_mode":"remix","intent":"Promote real office chairs to buyers"}
        project=client.post("/api/projects",json=payload).json()
        pid=project["id"]
        res=client.post(f"/api/projects/{pid}/reference",
            files={"file":("previous_reel.mp4",io.BytesIO(movie),"video/mp4")})
        assert res.status_code==201, res.text
        assert res.json()["reference"]["has_audio"]
        assert client.get(f"/api/projects/{pid}/reference/audio").status_code==200
        assert client.get(f"/api/projects/{pid}/reference/media").status_code==200
        for role in ("hero","detail"):
            r=client.post(f"/api/projects/{pid}/clips",data={"role":role},
                files={"file":(role+".mp4",io.BytesIO(movie),"video/mp4")})
            assert r.status_code==201,r.text
        bad=client.post(f"/api/projects/{pid}/renders",json={
            "styles":["stomp"],"audio_source":"reference","reference_start":5,"reference_seconds":8})
        assert bad.status_code==422
        good=client.post(f"/api/projects/{pid}/renders",json={
            "styles":["stomp"],"audio_source":"reference","reference_seconds":8})
        assert good.status_code==202,good.text
        state=client.get(f"/api/projects/{pid}").json()
        assert state["job"]["status"]=="ready",state["job"]
        mp4=client.get(state["exports"]["stomp"]["preview"])
        assert mp4.status_code==200 and len(mp4.content)>20000

def test_silent_reference_is_flagged(tmp_path):
    movie=video_with_audio(tmp_path,False)
    with TestClient(create_app(tmp_path/"store")) as client:
        pid=client.post("/api/projects",json={
            "source_mode":"remix","intent":"Create chair marketing videos"}).json()["id"]
        response=client.post(f"/api/projects/{pid}/reference",
            files={"file":("silent.mp4",io.BytesIO(movie),"video/mp4")})
        assert response.status_code==201
        assert not response.json()["reference"]["has_audio"]
        assert client.get(f"/api/projects/{pid}/reference/audio").status_code==409
