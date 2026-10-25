"""Instagram discovery assets: truthful buyer-specific copy, not keyword stuffing.

Product name, verified details, brand and served location only come from the
user's creative brief. Conversion goal is qualified conversations, not views.
"""
from __future__ import annotations
import re

STYLES = {
    "stomp": "Office chairs in action",
    "cinematic": "Take a closer look at the chair",
    "features": "What to check before buying an office chair",
    "business": "Office chairs for teams and workspaces",
    "social": "Looking for an office chair?",
    "voice_story": "A closer look at our office chairs",
}

def _compact(value: str, limit: int) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())[:limit].strip(" .,;")

def _hashtag(words: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", words.title())
    return "#" + cleaned if cleaned else ""

def _is_b2b(brief) -> bool:
    subject = f"{getattr(brief,'intent','')} {getattr(brief,'audience','')}".lower()
    return any(x in subject for x in ("bulk","b2b","office setup","furnish",
                                    "startup","procurement","corporate","team seating"))

def social_assets(brief, style: str) -> dict:
    if style not in STYLES:
        raise ValueError("Unknown Reel style")
    name = _compact(getattr(brief, "brand_name", "") or "Our showroom", 70)
    product = _compact(getattr(brief, "product", "") or "Office chair", 85)
    location = _compact(getattr(brief, "location", ""), 60)
    offer = _compact(getattr(brief, "offer", ""), 160)
    facts = _compact(getattr(brief, "facts", ""), 170)
    requested_cta = _compact(getattr(brief, "call_to_action", ""), 110)
    is_b2b = style == "business" or _is_b2b(brief)
    geo = f" in {location}" if location else ""
    title = f"{STYLES[style]}{geo}"
    first = f"{product}{geo} | {name}"
    if is_b2b:
        # Default is deliberately a qualified, structured DM not generic engagement.
        default_cta = "DM OFFICE + the number of chairs you need to ask about current options."
        cta = requested_cta if requested_cta and requested_cta.lower() not in (
            "dm us for availability", "dm us for details", "message us"
        ) else default_cta
        detail = (facts + ".") if facts else (
            "A closer look at the actual chair, from the backrest and seat to its finish."
        )
        caption = "\n\n".join(p for p in (
            f"{first}.",
            f"Furnishing an office or planning seating for your team? "
            f"See the actual chairs and ask about current options. {detail}",
            (offer.rstrip(".") + ".") if offer else "",
            cta.rstrip(".") + ".",
            " ".join(filter(None, [
                "#OfficeChairs", "#OfficeFurniture", "#OfficeSeating",
                "#WorkspaceSetup", _hashtag(location+" Furniture") if location else ""
            ]))
        ) if p)
        cover_title = "OFFICE CHAIRS FOR YOUR TEAM" if style == "business" else _compact(title, 66)
        pinned_comment = ("Planning seating for an office? "
                          "DM OFFICE + your chair count to enquire about current options.")
    else:
        cta = requested_cta or "DM CHAIR to ask about current options"
        detail = (facts + ".") if facts else "See the actual chair from different angles."
        caption = "\n\n".join(p for p in (
            f"{first}.", f"{title}. {detail}",
            (offer.rstrip(".")+".") if offer else "",
            cta.rstrip(".")+".",
            " ".join(filter(None, [
                "#OfficeChairs","#OfficeFurniture",
                _hashtag(location+" Furniture") if location else ""
            ]))
        ) if p)
        cover_title = _compact(title, 70)
        pinned_comment = f"Interested in {product}? {cta.rstrip('.')}."
    alt = (f"Vertical Reel showing actual {product} footage, with close-up views "
           f"and office seating context from {name}"
           + (f" in {location}" if location else "") + ".")
    terms=[product.lower(),"office chairs","office furniture","office seating"]
    if is_b2b:terms.extend(["office chairs for teams", "office chair enquiries"])
    if location:terms.extend([f"{product.lower()} {location.lower()}",
                              f"office chairs in {location.lower()}"])
    return {
        "cover_title": cover_title,
        "caption": caption,
        "alt_text": alt,
        "pinned_comment": pinned_comment,
        "search_phrases": list(dict.fromkeys(terms)),
        "primary_action": "Qualified DM with chair count" if is_b2b else "Qualified product enquiry",
        "checklist": [
            "Ensure every product and inventory shot shows a genuine item, not illustrative stock.",
            "Check first 2 seconds and title safe zones on an actual phone.",
            "Include only verified product details, commercial claims and service areas.",
            "Use a few relevant hashtags; avoid keyword stuffing.",
            "Track qualified DMs, saves, shares and watch time, not views alone."
        ]
    }
