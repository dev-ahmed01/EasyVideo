"""Guard the minimal browser client against accidental one-element list bindings."""
from pathlib import Path
import re

SOURCE=(Path(__file__).resolve().parents[1] / "web" / "app.js").read_text("utf-8")


def test_reel_lab_audio_controls_bind_all_buttons():
    assert '$$("[data-audio]").forEach' in SOURCE
    assert re.search(r'(?<!\$)\$\("\[data-audio\]"\)\.forEach', SOURCE) is None
    assert all(f'data-audio="{key}"' in SOURCE for key in ("reference", "generated", "uploaded"))


def test_six_style_gallery_and_narration_upload():
    assert '"voice_story"' in SOURCE
    assert 'audio_source:audioMode' in SOURCE
    assert '/narration","POST",form' in SOURCE
