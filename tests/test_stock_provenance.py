import io
import shutil
import subprocess
import sqlite3
from fastapi.testclient import TestClient
import pytest
from easyvideo.creative import Brief, audit
from easyvideo.director_v2 import _choose, STYLE_SHOTS
from easyvideo.server import create_app

def clip(role,origin="real"):
    return {"role":role,"source_type":origin,"filename":f"{role}.mp4","duration":4,
            "width":720,"height":1280}

def test_business_benchmark_requires_real_product_proof():
    b=Brief(intent="Sell office chairs in bulk to startups furnishing offices")
    only_stock=[clip("hero"),clip("detail"),clip("inventory","stock"),
                clip("office_context","stock"),clip("office_context","stock")]
    status=audit(b,only_stock)
    assert not status["ready"]
    assert any(x["role"]=="inventory" for x in status["missing"])
    actual=[clip("hero"),clip("detail"),clip("inventory"),
            clip("office_context","stock"),clip("office_context","stock")]
    ready=audit(b,actual)
    assert ready["ready"] and ready["stock_benchmark_ready"]
    assert ready["illustrative_stock_count"]==2

def test_stock_is_not_product_hero():
    clips=[clip("hero"),clip("hero","stock"),clip("inventory"),
           clip("office_context","stock")]
    selected,_=_choose("hero",clips,{},0,"business")
    assert selected["source_type"]=="real"
    assert STYLE_SHOTS["business"][0][0]=="office_context"

@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_upload_stock_cannot_become_inventory_or_proof(tmp_path):
    movie=tmp_path/"stock.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i",
                    "color=c=blue:s=360x640:r=24","-t","2",
                    "-c:v","libx264","-preset","ultrafast",str(movie)],
                   check=True,timeout=45)
    with TestClient(create_app(tmp_path/"app")) as api:
        pid=api.post("/api/projects",json={"intent":"Sell office chairs in bulk to offices"}).json()["id"]
        upload=lambda role:api.post(f"/api/projects/{pid}/clips",
            data={"role":role,"source_type":"stock"},
            files={"file":("stock.mp4",io.BytesIO(movie.read_bytes()),"video/mp4")})
        assert upload("inventory").status_code==422
        allowed=upload("office_context")
        assert allowed.status_code==201,allowed.text
        assert allowed.json()["clips"][0]["source_type"]=="stock"
        cid=allowed.json()["clips"][0]["id"]
        assert api.patch(f"/api/projects/{pid}/clips/{cid}",json={"role":"proof"}).status_code==422

def test_old_database_auto_migration(tmp_path):
    location=tmp_path/"app";location.mkdir()
    con=sqlite3.connect(location/"projects.sqlite3")
    con.executescript("""CREATE TABLE clips (
        id TEXT PRIMARY KEY, project_id TEXT, filename TEXT, stored_name TEXT,
        role TEXT, width INTEGER, height INTEGER, duration REAL);
    INSERT INTO clips VALUES ('x','old','chair.mp4','x.mp4','hero',720,1280,4);
    """)
    con.commit();con.close()
    create_app(location)
    with sqlite3.connect(location/"projects.sqlite3") as con:
        assert con.execute("SELECT source_type FROM clips WHERE id='x'").fetchone()[0]=="real"
