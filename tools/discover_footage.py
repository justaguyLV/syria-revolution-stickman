"""Search Commons for candidate footage and dump JSON + thumbnail contact sheets (for human/AI vetting)."""
import json, os, sys, io, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commons as C
from PIL import Image, ImageDraw

queries = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip() and not l.startswith("#")]
out = sys.argv[2]; os.makedirs(out, exist_ok=True)
res = {}
for q in queries:
    row = {}
    for kind in ("video", "photo"):
        try:
            row[kind] = C.search(q, kind, 10)
        except Exception as e:
            row[kind] = []; print("ERR", q, kind, e)
    res[q] = row
    print(f"{q}: {len(row['video'])} videos, {len(row['photo'])} photos", flush=True)
json.dump(res, open(os.path.join(out, "candidates.json"), "w"), ensure_ascii=False, indent=1)

# contact sheets
for qi, (q, row) in enumerate(res.items()):
    items = row["video"][:6] + row["photo"][:6]
    if not items: continue
    sheet = Image.new("RGB", (6 * 240, 2 * 190), (30, 30, 30)); d = ImageDraw.Draw(sheet)
    for i, it in enumerate(items):
        x, y = (i % 6) * 240, (i // 6) * 190
        try:
            req = urllib.request.Request(it["thumb"] or it["url"], headers=C.UA)
            im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB"); im.thumbnail((236, 150))
            sheet.paste(im, (x + 2, y + 2))
        except Exception: pass
        d.text((x + 4, y + 154), ("V " if it["kind"] == "video" else "P ") + it["title"][5:38], fill=(255, 255, 255))
        d.text((x + 4, y + 168), (it["license"] or "")[:34], fill=(180, 220, 180))
    sheet.save(os.path.join(out, f"q{qi:02d}.jpg"), quality=70)
print("done")
