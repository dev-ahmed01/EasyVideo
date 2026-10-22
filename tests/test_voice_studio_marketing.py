"""Loopback-only VoiceStudio integration and Instagram discovery coverage."""
from pathlib import Path
import json
import pytest
from easyvideo import voicestudio_bridge as studio
from easyvideo.creative import Brief
from easyvideo.marketing import social_assets

class Response:
    def __init__(self,data): self.data=data
    def __enter__(self): return self
    def __exit__(self,*a): return None
    def read(self,size): return self.data[:size]

def test_rejects_remote_speech_urls(monkeypatch):
    for url in ("https://example.com:3900","http://192.168.0.2:3900",
                "http://127.0.0.1:3900/other"):
        monkeypatch.setenv("EASYVIDEO_VOICESTUDIO_URL",url)
        with pytest.raises(studio.VoiceStudioError):studio._base_url()
    monkeypatch.setenv("EASYVIDEO_VOICESTUDIO_URL","http://127.0.0.1:3900")
    assert studio._base_url()=="http://127.0.0.1:3900"

def test_speech_api_local_wav(monkeypatch,tmp_path):
    calls=[]
    payload_audio=b"RIFF"+b"\x00"*4+b"WAVE"+b"x"*300
    class Opener:
        def open(self,request,timeout):
            calls.append((request.full_url,request.data))
            return Response(payload_audio)
    monkeypatch.setattr(studio.urllib.request,"build_opener",lambda *a:Opener())
    out=tmp_path/"voice.wav"
    assert studio.synthesize("Meet your next office chair",out)=="voicestudio"
    assert out.read_bytes()==payload_audio
    assert calls[0][0]=="http://127.0.0.1:3900/v1/audio/speech"
    data=json.loads(calls[0][1])
    assert data["response_format"]=="wav"
    assert data["input"]=="Meet your next office chair"

def test_reject_non_audio_api(monkeypatch,tmp_path):
    class Opener:
        def open(self,request,timeout):return Response(b'{"error":"unknown voice"}')
    monkeypatch.setattr(studio.urllib.request,"build_opener",lambda *a:Opener())
    with pytest.raises(studio.VoiceStudioError,match="did not return WAV"):
        studio.synthesize("Hello",tmp_path/"bad.wav")

def test_truthful_search_assets_without_location():
    b=Brief(intent="Organic office chair Reel",product="Commercial office chair",brand_name="Sample Office")
    pack=social_assets(b,"business")
    assert "Bengaluru" not in str(pack)
    assert "discount" not in str(pack).lower()
    assert "Commercial office chair" in pack["caption"]
    assert pack["alt_text"] and pack["pinned_comment"]

def test_location_only_when_stated():
    b=Brief(intent="Office chairs",product="Office chair",location="Bengaluru")
    pack=social_assets(b,"stomp")
    assert "Bengaluru" in pack["caption"]
    assert "#BengaluruFurniture" in pack["caption"]

def test_project_includes_six_search_packs(tmp_path):
    from easyvideo.server import create_app
    from fastapi.testclient import TestClient
    with TestClient(create_app(tmp_path)) as client:
        r=client.post("/api/projects",json={"intent":"Promote chairs organically","location":"Bengaluru"})
        assert r.status_code==201,r.text
        pack=r.json()["social_pack"]
        assert len(pack)==6
        assert "Bengaluru" in pack["cinematic"]["caption"]
