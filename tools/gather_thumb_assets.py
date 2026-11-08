"""Download free-licensed photos from Wikimedia Commons for the thumbnail + build a contact sheet."""
import json, os, sys, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from commons import _get, UA, _strip, search
from PIL import Image, ImageDraw

OUT = "thumb_assets"; os.makedirs(OUT, exist_ok=True)
TITLES = [
 "File:Damascus, Syria, Panoramic view of Damascus.jpg",
 "File:Hundreds of thousands of demonstrators in Hama demanding the downfall of the regime.jpg",
 "File:Syrians with opposition and Saudi Arabian flags on the abandoned tank of the Syrian Assad's forces after collapse of the regime.jpg",
 "File:Free Syrian Army soldier walking among rubble in Aleppo.jpg",
 "File:درعا البلد إحدى المظاهرات في بداية الإحتجاجات 2013-10-11 16-41.jpeg",
]
QUERIES = ["Syrian revolution flag protest", "Syrian opposition flag crowd Damascus 2024", "Umayyad Mosque Damascus",
           "Syrian independence flag green white black", "fall of Assad regime celebration Damascus", "Syrian revolution protest Idlib flag"]

def info(title):
    d = _get({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1600})
    p = (d.get("query", {}).get("pages") or [{}])[0]
    ii = (p.get("imageinfo") or [None])[0]
    if not ii: return None
    md = ii.get("extmetadata", {})
    return {"title": title, "url": ii.get("thumburl") or ii.get("url"), "w": ii.get("width"), "h": ii.get("height"),
            "license": md.get("LicenseShortName", {}).get("value", ""), "artist": _strip(md.get("Artist", {}).get("value", ""))[:80],
            "page": ii.get("descriptionurl")}

items = []
for t in TITLES:
    try:
        i = info(t)
        if i: items.append(i)
    except Exception as e: print("ERR", t, e)
for q in QUERIES:
    try:
        for r in search(q, "photo", 6)[:4]:
            if r["w"] and r["w"] >= 1200 and not any(x["title"] == r["title"] for x in items):
                i = info(r["title"])
                if i: items.append(i)
    except Exception as e: print("ERR", q, e)

meta = []
for n, it in enumerate(items):
    if not it["url"]: continue
    fn = f"{n:02d}.jpg"
    try:
        req = urllib.request.Request(it["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r: data = r.read()
        im = open(os.path.join(OUT, fn), "wb"); im.write(data); im.close()
        Image.open(os.path.join(OUT, fn)).convert("RGB").save(os.path.join(OUT, fn), quality=93)
        it["file"] = fn; meta.append(it); print(fn, it["license"], it["title"][:70])
    except Exception as e: print("DL-ERR", it["title"][:60], e)
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False, indent=1)

# contact sheet
cols, tw, th = 4, 400, 260
rows = (len(meta) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, max(1, rows) * th), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, m in enumerate(meta):
    im = Image.open(os.path.join(OUT, m["file"])); im.thumbnail((tw, th - 22))
    sheet.paste(im, ((i % cols) * tw, (i // cols) * th)); d.text(((i % cols) * tw + 4, (i // cols) * th + th - 18), f"{m['file']} {m['w']}x{m['h']} {m['license'][:14]}", fill=(255, 255, 0))
sheet.save(os.path.join(OUT, "sheet.jpg"), quality=88)
