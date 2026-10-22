"""Validate local Piper preference and modern CLI arguments without external downloads."""
from pathlib import Path
from types import SimpleNamespace

from easyvideo import voice


def test_piper_detects_local_voice_model(tmp_path, monkeypatch):
    model=tmp_path/"voice.onnx"
    model.write_bytes(b"fake model bytes")
    Path(str(model)+".json").write_text('{"audio":{"sample_rate":22050}}')
    monkeypatch.setenv("EASYVIDEO_PIPER_MODEL",str(model))
    monkeypatch.setattr(voice.importlib.util,"find_spec",lambda name: object() if name=="piper" else None)
    assert voice.configured_piper_model()==model
    assert "piper" in voice.engines()

def test_modern_piper_command_produces_wav(tmp_path,monkeypatch):
    model=tmp_path/"voice.onnx"
    model.write_bytes(b"model bytes")
    Path(str(model)+".json").write_text("{}")
    monkeypatch.setenv("EASYVIDEO_PIPER_MODEL",str(model))
    monkeypatch.setattr(voice.importlib.util,"find_spec",lambda name: object() if name=="piper" else None)
    observed=[]
    def fake_run(command,**kwargs):
        observed.extend(command)
        idx=command.index("-f")
        Path(command[idx+1]).write_bytes(b"RIFF"+b"0"*200)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(voice.subprocess,"run",fake_run)
    out=tmp_path/"voice.wav"
    assert voice.synthesize("Hello from EasyVideo",out,"piper")=="piper"
    assert observed[1:3]==["-m","piper"]
    assert observed[3:5]==["-m",str(model.resolve())]
    assert observed[-2:]==["--","Hello from EasyVideo"]

def test_piper_requires_companion_configuration(tmp_path,monkeypatch):
    model=tmp_path/"broken.onnx"
    model.write_bytes(b"fake")
    monkeypatch.setenv("EASYVIDEO_PIPER_MODEL",str(model))
    assert voice.configured_piper_model() is None
