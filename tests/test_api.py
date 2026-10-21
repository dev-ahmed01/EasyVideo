import io
from fastapi.testclient import TestClient
from easyvideo.server import create_app

BRIEF = {"intent":"Promote commercial chair stock to home office buyers and drive DMs",
         "product":"Mesh office chair","call_to_action":"DM for availability"}

def test_intent_first_project_and_missing_shot(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        res = client.post("/api/plan",json=BRIEF)
        assert res.status_code == 200
        assert len(res.json()["creatives"]) == 5
        assert {x["role"] for x in res.json()["shotlist"] if x["required"]} == {"hero","detail"}
        r = client.post("/api/projects",json=BRIEF)
        assert r.status_code == 201
        pid = r.json()["id"]
        assert r.json()["audit"]["ready"] is False
        bad = client.post(f"/api/projects/{pid}/clips",data={"role":"hero"},
                          files={"file":("fake.txt",io.BytesIO(b"not a video"),"text/plain")})
        assert bad.status_code == 415
        blocked = client.post(f"/api/projects/{pid}/renders",json={"styles":["stomp"]})
        assert blocked.status_code == 409
        assert "Missing required shots" in blocked.json()["detail"]
        assert client.get("/api/projects").json()[0]["id"] == pid
        assert client.post(f"/api/projects/{pid}/selection",json={"styles":["stomp","features"]}).status_code == 200
        assert client.post(f"/api/projects/{pid}/selection",json={"styles":["wrong"]}).status_code == 422
        assert client.get(f"/api/projects/{pid}/exports/stomp/preview").status_code == 404

def test_media_validation_rejects_bogus_movie(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        pid=client.post("/api/projects",json=BRIEF).json()["id"]
        r=client.post(f"/api/projects/{pid}/clips",data={"role":"hero"},
                      files={"file":("fake.mp4",io.BytesIO(b"this isn't a movie"),"video/mp4")})
        assert r.status_code == 422
        assert client.get(f"/api/projects/{pid}").json()["clips"] == []
