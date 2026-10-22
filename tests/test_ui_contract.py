"""Contract checks for the tiny dependency-free browser UI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_reel_lab_soundtrack_buttons_use_multi_selector():
    source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert '$$("[data-audio]").forEach' in source
    assert '$("[data-audio]").forEach' not in source
    assert 'data-audio="uploaded"' in source
    assert 'data-audio="reference"' in source
    assert 'data-audio="generated"' in source

def test_six_styles_and_new_voice_mode_present():
    source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert '"voice_story"' in source
    assert '"POST",form' in source
    assert '"audio_source:audioMode"' not in source
    assert 'audio_source:audioMode' in source
