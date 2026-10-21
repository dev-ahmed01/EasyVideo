from easyvideo.creative import Brief, STYLES, audit, creatives, required_shots

def test_five_distinct_marketing_ideas():
    brief = Brief(intent="Generate organic office chair enquiries", product="Office chair", facts="Breathable mesh", offer="Stock available")
    ideas = creatives(brief)
    assert len(ideas) == 5
    assert {idea["id"] for idea in ideas} == set(STYLES)
    assert len({idea["beats"][0] for idea in ideas}) == 5
    assert all(idea["voiceover"] and len(idea["beats"]) == 4 for idea in ideas)

def test_pasted_script_remains_in_feature_narration():
    brief = Brief(intent="Attract workstation buyers", script="This is the exact script I approved.")
    idea = next(x for x in creatives(brief) if x["id"] == "features")
    assert idea["voiceover"] == "This is the exact script I approved."

def test_bulk_intent_demands_inventory_footage():
    brief = Brief(intent="Reach startups buying bulk office chairs and set up their workplace")
    required = {x["role"] for x in required_shots(brief) if x["required"]}
    assert required == {"hero", "detail", "inventory"}
    sample = [{"filename":"h.mp4","role":"hero","duration":5,"width":1080,"height":1920},
              {"filename":"d.mp4","role":"detail","duration":5,"width":1080,"height":1920}]
    check = audit(brief,sample)
    assert check["ready"] is False
    assert check["missing"][0]["role"] == "inventory"
    sample.append({"filename":"inventory.mp4","role":"inventory","duration":5,"width":1080,"height":1920})
    assert audit(brief,sample)["ready"]

def test_file_warning_detects_landscape_and_low_resolution():
    brief = Brief(intent="Advertise ergonomic office chair")
    clips = [{"filename":"h.mp4","role":"hero","duration":5,"width":320,"height":240},
             {"filename":"d.mp4","role":"detail","duration":5,"width":320,"height":240}]
    output = audit(brief, clips)
    assert output["ready"]
    assert any("low resolution" in w for w in output["warnings"])
    assert any("center-cropped" in w for w in output["warnings"])

def test_caption_and_cover_available_for_each_reel():
    results=creatives(Brief(intent="Promote a chair to buyers",product="Office chair"))
    assert all(len(row["caption"])>20 and row["cover_title"] for row in results)
    assert len({row["marketing_goal"] for row in results})==5

def test_campaign_hooks_depend_on_audience():
    business=creatives(Brief(intent="Office chairs for bulk startup office furnishing"))
    home=creatives(Brief(intent="Ergonomic chair for WFH home office"))
    assert next(x for x in business if x["id"]=="social")["beats"][0]=="SETTING UP AN OFFICE?"
    assert next(x for x in home if x["id"]=="social")["beats"][0]=="HOME OFFICE UPGRADE?"
