# © 2026 Power Palm. All rights reserved. See LICENSE.
"""Add English names and exact map pins from OpenStreetMap to data.json.

Inputs (in sources/):
- osm_msheireb.json    places from OpenStreetMap, already limited to Msheireb Downtown's
                       official outline (OSM relation 309833, "مشيرب قلب الدوحة")
- msheireb_outline.json that outline, used to double-check every pin

Outputs:
- data.json            each matched place gets "en", "lat", "lon"; places without a written
                       "location" get a "near" note worked out from the pins
- sources/to_review.md places OpenStreetMap has but data.json doesn't, for a person to check

Run from the project folder:  python tools/enrich_from_osm.py
Later, the same step can read Google Places or Msheireb's official directory instead.
Map data © OpenStreetMap contributors (ODbL).
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OSM = json.loads((ROOT / "sources/osm_msheireb.json").read_text(encoding="utf-8"))
OUTLINE = json.loads((ROOT / "sources/msheireb_outline.json").read_text(encoding="utf-8"))

# OpenStreetMap name -> (name in data.json, English name to show). Checked by hand.
MATCH = {
    "Saasna": ("ساسنا", "Saasna"),
    "% Arabica": ("أرابيكا", "% Arabica"),
    "Rusk Artisanal Bakery": ("رسك", "Rusk Artisanal Bakery"),
    "Turkiani": ("تركيانا", "Turkiani"),
    "Trapani": ("ترباني", "Trapani"),
    "Nourlaya": ("نورلايا", "Nourlaya"),
    "IZU": ("إيزو", "IZU"),
    "Gelato": ("جيلاتو", "Gelato"),
    "Bau": ("باو", "Bau"),
    "Santa Nata": ("سانتا ناتا", "Santa Nata"),
    "Cloud & Co": ("كلاود و كو", "Cloud & Co"),
    "Liang": ("ليانغ", "Liang"),
    "Savant Coffee Shop": ("سافانت", "Savant Coffee"),
    "Ramen": ("رامين", "Ramen"),
    "Nisrine": ("نسرين", "Nisrine"),
    "Yoza": ("يوزه", "Yoza"),
    "Crust": ("كراست باي راسك", "Crust by Rusk"),
    "Toby’s estate": ("توبيز استيت", "Toby's Estate"),
    "Harrods Tea Rooms": ("هارودز تي رووم", "Harrods Tea Rooms"),
    "Qinwan": ("قنوان", "Qinwan"),
    "Earth": ("ايرث", "Earth"),
    "The Buttery Bakery": ("ذي باتري باكري", "The Buttery Bakery"),
    "Cicchetti": ("شيكيتي", "Cicchetti"),
    "Profiles by roastado": ("بروفايلس", "Profiles by Roastado"),
    "Ministry of Coffee": ("ذا مينستري اوف كوفي", "The Ministry of Coffee"),
    "Bin Jelmood House": ("متاحف مشيرب: بيت بن جلمود", "Msheireb Museums: Bin Jelmood House"),
    "Company House": ("متاحف مشيرب: بيت الشركة", "Msheireb Museums: Company House"),
    "Mohammed Bin Jassim House": ("متاحف مشيرب: بيت محمد بن جاسم", "Msheireb Museums: Mohammed Bin Jassim House"),
    "Radwani house": ("متاحف مشيرب: بيت الرضواني", "Msheireb Museums: Radwani House"),
    "M7": ("M7", "M7"),
    "مشيرب": ("محطة مترو مشيرب", "Msheireb Metro Station"),
    "Msheireb Galleria": ("مشيرب غاليريا", "Msheireb Galleria"),
    "Monoprix": ("مونوبري", "Monoprix"),
    "Casio": ("كاسيو", "Casio"),
    "Yateem": ("نظارات يتيم", "Yateem Optician"),
    "Ebnsina Pharmacy": ("صيدلية ابن سينا", "Ibn Sina Pharmacy"),
}
# OpenStreetMap entries that are not visitor places, or too vague to use.
SKIP = {"متحف مشيرب", "Qasr Al hukum", "Barahat Msherib 1"}

# Well-known buildings visitors can see, used to describe where a place is ("near" notes).
LANDMARKS = {
    "Mandarin Oriental": "Mandarin Oriental Doha",
    "Park Hyatt": "Park Hyatt Doha",
    "Al Wadi Hotel": "Al Wadi Hotel",
    "Msheireb Galleria": "Msheireb Galleria",
    "M7": "M7",
    "Bin Jelmood House": "Bin Jelmood House (Msheireb Museums)",
    "مشيرب": "Msheireb Metro Station",
    "Harrods Tea Rooms": "Harrods Tea Rooms on Barahat Msheireb square",
}


def pin(e):
    return (e.get("lat") or e["center"]["lat"], e.get("lon") or e["center"]["lon"])


def inside_outline(lat, lon):
    hit, n = False, len(OUTLINE)
    for i in range(n):
        x1, y1 = OUTLINE[i]
        x2, y2 = OUTLINE[(i + 1) % n]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def metres(a, b):
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy), dx, dy


def direction(dx, dy):
    names = ["east", "north-east", "north", "north-west", "west", "south-west", "south", "south-east"]
    return names[round(math.degrees(math.atan2(dy, dx)) / 45) % 8]


def near_note(p):
    here = (p["lat"], p["lon"])
    options = []
    for osm_name, label in LANDMARKS.items():
        e = next((x for x in OSM if x["tags"]["name"] == osm_name), None)
        if e and label.split(" (")[0] not in (p.get("en") or ""):
            d, dx, dy = metres(here, pin(e))
            options.append((d, dx, dy, label))
    d, dx, dy, label = min(options)
    if d < 40:
        return f"Right next to {label}."
    return f"About {round(d / 10) * 10} m {direction(dx, dy)} of {label}."


def main():
    lines = (ROOT / "data.json").read_text(encoding="utf-8").strip().splitlines()
    places = [json.loads(l.rstrip(",")) for l in lines[1:-1]]
    by_name = {p["name"]: p for p in places}

    review = []
    for e in OSM:
        t = e["tags"]
        lat, lon = pin(e)
        assert inside_outline(lat, lon), t["name"]
        if t["name"] in SKIP:
            continue
        if t["name"] in MATCH:
            ar, en = MATCH[t["name"]]
            p = by_name[ar]
            p["en"], p["lat"], p["lon"] = en, round(lat, 5), round(lon, 5)
        else:
            kind = t.get("amenity") or t.get("shop") or t.get("tourism") or t.get("leisure") or ""
            review.append((kind, t["name"], round(lat, 5), round(lon, 5)))

    for p in places:
        if "lat" in p and "location" not in p:
            p["near"] = near_note(p)

    # Keep data.json readable: one place per line, key order: name, en, then the rest.
    def ordered(p):
        keys = ["name", "en"] + [k for k in p if k not in ("name", "en", "lat", "lon")] + ["lat", "lon"]
        return {k: p[k] for k in keys if k in p}
    body = ",\n".join(json.dumps(ordered(p), ensure_ascii=False) for p in places)
    (ROOT / "data.json").write_text("[\n" + body + "\n]\n", encoding="utf-8")

    rows = "\n".join(f"| {k} | {n} | {la}, {lo} | https://www.google.com/maps?q={la},{lo} |"
                     for k, n, la, lo in sorted(review))
    (ROOT / "sources/to_review.md").write_text(
        "# Places in OpenStreetMap but not in data.json\n\n"
        "OpenStreetMap can be out of date. Check each one is still open before adding it.\n\n"
        "| Kind | Name | Pin | Check on the map |\n|---|---|---|---|\n" + rows + "\n", encoding="utf-8")

    pinned = sum("lat" in p for p in places)
    print(f"{pinned} of {len(places)} places now have an English name and an exact pin; "
          f"{sum('near' in p for p in places)} got a 'near' note; {len(review)} new places to review.")


if __name__ == "__main__":
    main()
