"""Piper 1.8+ CLI regression checks, no actual voice weights required."""
from pathlib import Path
from types import SimpleNamespace
from easyvideo import voice


def test_modern_piper_prefers_local_model_and_speaker(tmp_path, monkeypatch):
    model=tmp_path/"voice.onnx"
    model.write_bytes(b"test")
    Path(str(model)+".json").write_text("{}")
    monkeypatch.setenv("EASYVIDEO_PIPER_MODEL",str(model))
    monkeypatch.setenv("EASYVIDEO_PIPER_SPEAKER","676")
    monkeypatch.setattr(voice, "_modern_piper_installed",lambda: True)
    assert voice._piper_model()==model
    assert voice.engines()[0]=="piper"
    commands=[]
    def fake_run(cmd, **kw):
        commands.append(cmd)
        Path(cmd[cmd.index("-f")+1]).write_bytes(b"RIFF"+b"x"*200)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(voice.subprocess,"run",fake_run)
    out=tmp_path/"narration.wav"
    assert voice.synthesize("A better workspace",out,"piper")=="piper"
    assert commands[0][1:3]==["-m","piper"]
    assert commands[0][-4:]==["--speaker","676","--","A better workspace"]


def test_missing_companion_configuration_disables_piper(tmp_path, monkeypatch):
    model=tmp_path/"voice.onnx"
    model.write_bytes(b"some ONNX")
    monkeypatch.setenv("EASYVIDEO_PIPER_MODEL",str(model))
    assert voice._piper_model() is None
