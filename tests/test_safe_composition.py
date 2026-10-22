"""Guard against Instagram-overlay and product-framing regressions."""
from PIL import Image
from easyvideo.director_v2 import _graphic, crop_window, title_moments

def test_remove_baked_bars_and_fill_vertical():
    assert crop_window(0,160,720,960,540,960)==(90,160,540,960)
    assert crop_window(0,0,720,1280,540,960)==(0,0,720,1280)

def test_not_every_scene_gets_a_text_card():
    assert len(title_moments("cinematic",6))==2
    assert len(title_moments("business",7))==3
    assert len(title_moments("stomp",8))<=4

def test_title_and_brand_inside_safe_region(tmp_path):
    file=tmp_path/"card.png"
    _graphic(file,"FURNISHING AN OFFICE?","business",540,960,"Furnihub Interiors")
    box=Image.open(file).getchannel("A").getbbox()
    assert box
    left,top,right,bottom=box
    assert left>=int(540*.06)
    assert top>=int(960*.14)
    assert right<=int(540*.84)
    assert bottom<=int(960*.65)

def test_no_permanent_logo_when_scene_has_no_text(tmp_path):
    file=tmp_path/"empty.png"
    _graphic(file,"","cinematic",540,960,"Furnihub Interiors")
    assert Image.open(file).getchannel("A").getbbox() is None
