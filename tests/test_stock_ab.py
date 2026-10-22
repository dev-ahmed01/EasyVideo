"""A/B comparison uses exactly the same narration and real chair visuals."""
import io
import shutil
import subprocess
import wave

from fastapi.testclient import TestClient
from easyvideo.server import create_app
import easyvideo.server as server


def test_exact_matching_audio_between_control_and_stock(tmp_path,monkeypatch):
    # Metadata and rendering stubbed here; separate FFmpeg tests verify codecs.
    calls=[]
    def fake_render(brief,clips,style,project,resolution,**kwargs):
        calls.append({"style":style,"clips":[(c["role"],c["source_type"]) for c in clips],
                      "narration":str(kwargs["voiceover_file"])})
        target=project/"exports"/f"{style}_{resolution}.mp4"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(("MOVIE-"+str(len(calls))).encode())
        return target
    monkeypatch.setattr(server,"render_variant",fake_render)
    with TestClient(create_app(tmp_path/"app")) as client:
        pid=client.post("/api/projects",json={"intent":"Sell chairs in bulk to startups and offices"}).json()["id"]
        media=tmp_path/"media.mp4"
        subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",
                        "color=c=blue:s=360x640:r=24","-t","2",
                        "-c:v","libx264","-preset","ultrafast",str(media)],
                       check=True,timeout=40)
        for role,source in [("hero","real"),("detail","real"),("inventory","real"),
                            ("office_context","stock"),("office_context","stock")]:
            res=client.post(f"/api/projects/{pid}/clips",
                 data={"role":role,"source_type":source},
                 files={"file":(role+".mp4",io.BytesIO(media.read_bytes()),"video/mp4")})
            assert res.status_code==201, res.text
        with wave.open(str(tmp_path/"narration.wav"),"wb") as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000)
            audio.writeframes(b"\x00\x00"*16000*4)
        wav=(tmp_path/"narration.wav").read_bytes()
        upload=client.post(f"/api/projects/{pid}/narration",
                           files={"file":("human.wav",io.BytesIO(wav),"audio/wav")})
        assert upload.status_code==201, upload.text
        assert upload.json()["audit"]["stock_benchmark_ready"]
        result=client.post(f"/api/projects/{pid}/benchmarks",json={"resolution":"preview"})
        assert result.status_code==202,result.text
        proj=client.get(f"/api/projects/{pid}").json()
        assert proj["job"]["status"]=="ready", proj["job"]
        assert len(calls)==2
        assert calls[0]["narration"]==calls[1]["narration"]
        assert all(origin=="real" for _,origin in calls[0]["clips"])
        assert sum(origin=="stock" for _,origin in calls[1]["clips"])==2
        for variant in ("real_only","stock_mix"):
            assert client.get(proj["comparisons"][variant]["preview"]).status_code==200
