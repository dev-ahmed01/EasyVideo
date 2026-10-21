"""CPU-only encoder integration test with a synthetic fixture and synthetic narration."""
import shutil
import subprocess
import wave
import math
import struct

import pytest

from easyvideo.creative import Brief
from easyvideo.render import probe, probe_audio, render_variant
from easyvideo import render

@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg unavailable")
def test_render_real_video_with_narration(tmp_path, monkeypatch):
    footage=tmp_path/"chair.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i",
                    "color=c=blue:s=540x960:r=24","-t","4",
                    "-c:v","libx264","-preset","ultrafast",str(footage)],
                   check=True,timeout=50)
    project=tmp_path/"project"
    (project/"clips").mkdir(parents=True)
    target=project/"clips"/"clip.mp4"
    shutil.copyfile(footage,target)
    info=probe(target)
    assert info["width"] == 540
    def synth(text, out, preferred="auto"):
        with wave.open(str(out),"wb") as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000)
            for i in range(16000):
                s=int(1200*math.sin(2*math.pi*220*i/16000))
                audio.writeframesraw(struct.pack("<h",s))
        return "test"
    monkeypatch.setattr(render,"synthesize",synth)
    clip={"stored_name":"clip.mp4","filename":"chair.mp4","role":"hero",**info}
    result=render_variant(Brief(intent="Promote chair sales and organic enquiries"),
                          [clip],"stomp",project)
    assert result.is_file()
    assert probe(result)["duration"] > 9
    assert probe_audio(result) > 9
    p=subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
                      "-show_entries","stream=codec_name","-of","csv=p=0",str(result)],
                     capture_output=True,text=True,check=True)
    assert "aac" in p.stdout
