"""Organic Instagram search/discovery assets grounded in the supplied brief.

This is not a ranking or virality oracle. It does not invent geography,
pricing, stock, endorsements, materials, or guarantees.
"""
from __future__ import annotations
import re

STYLES = {
    "stomp": "A fresh look at office seating",
    "cinematic": "Office chair details worth noticing",
    "features": "What to check in an office chair",
    "business": "Office chairs for team workspaces",
    "social": "Looking for a chair for your desk?",
    "voice_story": "A closer look at our office chairs",
}
def _compact(value:str,limit:int)->str:
    return re.sub(r"\s+"," ",(value or "").strip())[:limit].strip(" .,;")

def _hashtag(words:str)->str:
    clean=re.sub(r"[^a-zA-Z0-9]","",words.title())
    return "#"+clean if clean else ""

def social_assets(brief,style:str)->dict:
    if style not in STYLES:raise ValueError("Unknown Reel style")
    name=_compact(getattr(brief,"brand_name","") or "Our showroom",70)
    product=_compact(getattr(brief,"product","") or "Office chair",85)
    location=_compact(getattr(brief,"location",""),60)
    offer=_compact(getattr(brief,"offer",""),160)
    facts=_compact(getattr(brief,"facts",""),170)
    cta=_compact(getattr(brief,"call_to_action","") or "DM CHAIR for current options",100)
    # Include at most one location phrase, only when explicitly entered by user.
    geo=f" in {location}" if location else ""
    headline=f"{STYLES[style]}{geo}"
    first=f"{product}{geo} | {name}"
    detail=facts or "See the real product finish, condition and angles in our footage."
    offer_line=(offer.rstrip(".")+".") if offer else ""
    caption="\n".join(x for x in (
        f"{first}.",
        f"{headline}.",
        f"{detail.rstrip('.')}.",
        offer_line,
        cta.rstrip(".")+".",
        " ".join(filter(None,[
            "#OfficeChairs","#OfficeFurniture",
            _hashtag(location+" Furniture") if location else ""
        ]))
    ) if x)
    alt=(f"Vertical video showing an actual {product} and its visible features, "
         f"with real chair and office footage from {name}"
         + (f" in {location}" if location else "") + ".")
    pinned=f"Interested in this {product}? {cta.rstrip('.')}."
    tags=[product.lower(),"office chairs","office furniture"]
    if location:tags.extend([f"{product.lower()} {location.lower()}",f"office chairs in {location.lower()}"])
    return {
        "cover_title": _compact(headline,70),
        "caption": caption,
        "alt_text": alt,
        "pinned_comment": pinned,
        "search_phrases": tags,
        "checklist": [
            "Publish the most accurate footage first; do not imply unverified features.",
            "Check the cover and first two seconds on a phone.",
            "Add a real location tag only if the business serves that area.",
            "Respond to genuine enquiries and track retention, sends and leads."
        ]
    }
