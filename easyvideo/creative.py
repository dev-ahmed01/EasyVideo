"""Marketing-first storyboard generation. No external AI calls or speculative claims."""
from __future__ import annotations

from dataclasses import dataclass
import re

ROLES = {
    "hero": ("Full chair / hero", "Capture the entire chair in a clean frame. Move slowly from front to 45 degrees."),
    "detail": ("Material / detail", "Record close-ups of mesh, upholstery, base, seams and finish."),
    "function": ("Real feature demonstration", "Show only functions the actual chair supports, preferably with hands in frame."),
    "workspace": ("Chair in a workspace", "Film the chair beside a real desk in a tidy office."),
    "inventory": ("Inventory / multiple chairs", "Show available stock or a genuine large-office installation."),
    "proof": ("Trust / business proof", "Show genuine showroom, packing, installation or real customer-approved footage."),
}
STYLES = {
    "stomp": {"title": "STOMP", "subtitle": "Bold type, beats, rapid cuts", "seconds": [2.1, 2.6, 2.5, 3.0], "roles": ["hero", "detail", "function", "hero"], "colors": ["#111827", "#d5ff56"]},
    "cinematic": {"title": "Cinematic", "subtitle": "Quiet confidence, elegant reveal", "seconds": [3.4, 4.1, 3.4, 3.8], "roles": ["detail", "hero", "workspace", "hero"], "colors": ["#0c1d1a", "#e8dfc9"]},
    "features": {"title": "Smart buyer", "subtitle": "Useful, save-worthy office chair tips", "seconds": [2.6, 3.6, 3.6, 3.2], "roles": ["hero", "function", "detail", "hero"], "colors": ["#163b43", "#8fe0da"]},
    "business": {"title": "Office solutions", "subtitle": "A practical, trust-first B2B story", "seconds": [3.2, 3.1, 3.6, 3.4], "roles": ["workspace", "inventory", "detail", "hero"], "colors": ["#192b47", "#e3b873"]},
    "social": {"title": "Social-native", "subtitle": "Conversational hook and short beats", "seconds": [1.8, 3.2, 2.9, 3.2], "roles": ["hero", "detail", "workspace", "hero"], "colors": ["#392754", "#e6b1ff"]},
}

@dataclass
class Brief:
    intent: str
    audience: str = "Office and work-from-home buyers"
    product: str = "Office chair"
    offer: str = ""
    facts: str = ""
    call_to_action: str = "DM us for availability"
    script: str = ""

def clean(value: str, limit: int = 240) -> str:
    value = re.sub(r"\s+", " ", (value or "")).strip()
    return value[:limit]

def required_shots(brief: Brief) -> list[dict]:
    subject = clean(brief.intent + " " + brief.audience, 1600).lower()
    required = {"hero", "detail"}
    if any(word in subject for word in ("bulk", "corporate", "office setup", "b2b", "startup", "furnish")):
        required.add("inventory")
    return [
        {"role": name, "label": label, "instruction": instruction, "required": name in required}
        for name, (label, instruction) in ROLES.items()
    ]

def _trim_words(text: str, max_words: int = 49) -> str:
    words = clean(text, 1800).split()
    return " ".join(words[:max_words]).rstrip("., ") + ("." if words else "")

def creatives(brief: Brief) -> list[dict]:
    product = clean(brief.product, 55) or "Office chair"
    cta = clean(brief.call_to_action, 65) or "DM us for details"
    offer = clean(brief.offer, 70)
    facts = clean(brief.facts, 110)
    # User-supplied facts are never expanded into unverified performance claims.
    factline = facts or "A closer look at the finish, form and everyday usability."
    offerline = offer or "Explore the available options."
    script = _trim_words(brief.script)
    intent = clean(brief.intent + " " + brief.audience, 1600).lower()
    bulk = any(word in intent for word in ("bulk", "startup", "corporate", "office setup", "b2b", "furnish"))
    home = any(word in intent for word in ("work from home", "home office", "remote work", "wfh"))
    budget = any(word in intent for word in ("budget", "affordable", "value", "cost-effective"))
    premium = any(word in intent for word in ("premium", "luxury", "cinematic", "high-end"))
    opener = "SETTING UP AN OFFICE?" if bulk else "HOME OFFICE UPGRADE?" if home else "BUYING A WORK CHAIR?"
    cinematic_hook = "THE DETAILS MATTER" if premium else "MEET YOUR NEXT CHAIR"
    shopper_hook = "SMARTER CHAIR SHOPPING" if budget else "BEFORE YOU BUY"
    data = [
        ("stomp", ["STOP SCROLLING", product.upper(), offerline.upper(), "ENQUIRE TODAY"],
         f"Looking for {product}? Take a closer look. {factline} {offerline} {cta}."),
        ("cinematic", [cinematic_hook, product, "A BETTER WORKSPACE", "DISCOVER MORE"],
         f"A workspace starts with the details. Introducing {product}. {factline} {cta}."),
        ("features", [shopper_hook, "LOOK CLOSELY", "CHECK THE DETAILS", "ASK US"],
         f"Choosing an office chair? Look closely at the build, material and condition. {factline} {cta}."),
        ("business", ["FURNISHING AN OFFICE?", "SEE WHAT IS AVAILABLE", "REAL WORKSPACES", "GET IN TOUCH"],
         f"Planning seating for a workspace? Explore {product} options for your office. {offerline} {cta}."),
        ("social", [opener, "HERE IS A CLOSER LOOK", "YOUR WORKSPACE, SORTED", "MESSAGE US"],
         f"Quick question. Is your current office chair working for your setup? Here's {product}. {factline} {cta}."),
    ]
    result = []
    for key, beats, voice in data:
        info = STYLES[key]
        # The supplied script becomes the narration in the feature-led style;
        # all other styles create distinct, truthful variations.
        if script and key == "features":
            voice = script
        result.append({
            "id": key, "title": info["title"], "subtitle": info["subtitle"],
            "beats": [clean(beat, 62) for beat in beats],
            "voiceover": _trim_words(voice), "roles": info["roles"],
            "estimated_seconds": round(sum(info["seconds"])),
            "cover_title": clean(beats[0], 65),
            "caption": clean(
                f"{product}: {factline} {offerline} {cta}. #OfficeFurniture #OfficeChairs #Workspace",
                420
            ),
            "marketing_goal": {
                "stomp": "Pattern interrupt / initial attention",
                "cinematic": "Premium perception",
                "features": "Saves and buying confidence",
                "business": "Office/bulk sales enquiries",
                "social": "Natural discovery and DMs",
            }[key]
        })
    return result

def audit(brief: Brief, clips: list[dict]) -> dict:
    shotlist = required_shots(brief)
    available = {clip["role"] for clip in clips if clip.get("duration", 0) >= 1}
    missing = [s for s in shotlist if s["required"] and s["role"] not in available]
    suggestions = [s for s in shotlist if not s["required"] and s["role"] not in available]
    warnings = []
    for clip in clips:
        if clip.get("duration", 0) < 2:
            warnings.append(f"{clip['filename']}: very short clip; aim for 3–6 seconds.")
        w, h = clip.get("width", 0), clip.get("height", 0)
        if w and h and min(w, h) < 540:
            warnings.append(f"{clip['filename']}: low resolution may reduce sharpness.")
        if w > h:
            warnings.append(f"{clip['filename']}: landscape footage will be center-cropped to vertical. Keep chair centered.")
    if clips:
        warnings.append("Shot roles are your labels; EasyVideo verifies file properties, not the actual visual subject. Review the previews.")
    return {
        "ready": bool(clips) and not missing,
        "missing": missing, "suggested": suggestions, "warnings": warnings,
        "uploaded": len(clips), "required_total": sum(bool(x["required"]) for x in shotlist),
        "matched_required": sum(bool(x["required"] and x["role"] in available) for x in shotlist)
    }
