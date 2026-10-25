"""Sales intent, Instagram post copy and truly voice-free rendering."""
import io
import shutil
import subprocess
import json

import pytest
from fastapi.testclient import TestClient
from easyvideo.creative import Brief, creatives
from easyvideo.marketing import social_assets
from easyvideo.server import create_app
import easyvideo.server as server
import easyvideo.render as renderer


def test_sales_copy_asks_for_qualified_chair_count():
    brief=Brief(intent="Furnish a startup office in bulk",product="Commercial office chair",
                brand_name="Furnihub Interiors")
    pack=social_assets(brief,"business")
    assert pack["primary_action"]=="Qualified DM with chair count"
    assert "DM OFFICE + the number of chairs" in pack["caption"]
    assert "Furnihub Interiors" in pack["caption"]
    assert "warranty" not in pack["caption"].lower()
    assert "discount" not in pack["caption"].lower()
    assert "Bengaluru" not in pack["caption"]
    assert pack["cover_title"]=="OFFICE CHAIRS FOR YOUR TEAM"
    assert "chair count" in pack["pinned_comment"].lower()


def test_search_copy_only_uses_provided_location_and_facts():
    b=Brief(intent="Office seating bulk purchase",product="Mesh office chair",
            location="Bengaluru",facts="Actual black chair with mesh back")
    pack=social_assets(b,"business")
    assert "Bengaluru" in pack["caption"]
    assert "Actual black chair with mesh back" in pack["caption"]
    assert "#BengaluruFurniture" in pack["caption"]


def test_business_on_screen_beats_are_sales_specific():
    b=Brief(intent="Furnishing a startup office")
    story=next(x for x in creatives(b) if x["id"]=="business")
    assert story["beats"][0]=="FURNISHING AN OFFICE?"
    assert story["beats"][-1]=="DM OFFICE + CHAIR COUNT"


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="Real FFmpeg clip required")
def test_generate_business_reel_without_any_voice_engine(tmp_path,monkeypatch):
    movie=tmp_path/"chair.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",
                    "color=c=darkgreen:s=360x640:r=24","-t","3",
                    "-c:v","libx264","-preset","ultrafast",str(movie)],
                   check=True,timeout=45)
    # If this calls TTS, the captions-first workflow is broken.
    monkeypatch.setattr(server,"engines",lambda: [])
    monkeypatch.setattr(renderer,"synthesize",
                        lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("TTS must not run")))
    with TestClient(create_app(tmp_path/"store")) as app:
        pid=app.post("/api/projects",json={
            "intent":"Sell chairs to offices in bulk",
            "product":"Office chair","brand_name":"Furnihub Interiors"
        }).json()["id"]
        for role in ("hero","detail","inventory"):
            result=app.post(f"/api/projects/{pid}/clips",
                            data={"role":role},
                            files={"file":(role+".mp4",io.BytesIO(movie.read_bytes()),"video/mp4")})
            assert result.status_code==201,result.text
        resp=app.post(f"/api/projects/{pid}/renders",
                      json={"styles":["business"],"resolution":"preview",
                            "audio_source":"music"})
        assert resp.status_code==202,resp.text
        state=app.get(f"/api/projects/{pid}").json()
        assert state["job"]["status"]=="ready",state["job"]
        got=app.get(state["exports"]["business"]["preview"])
        assert got.status_code==200 and len(got.content)>15000
        output=tmp_path/"check.mp4";output.write_bytes(got.content)
        info=json.loads(subprocess.check_output([
            "ffprobe","-v","error","-show_streams","-of","json",str(output)]))
        assert any(x["codec_type"]=="audio" for x in info["streams"])
        assert any(x["codec_type"]=="video" for x in info["streams"])
