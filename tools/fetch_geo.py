"""Fetch geo data for the epic map: Syria admin boundaries (geoBoundaries) + terrain tiles (AWS Terrarium, public).
usage: python tools/fetch_geo.py <outdir> [--probe]"""
import io, json, math, os, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]; PROBE = "--probe" in sys.argv
os.makedirs(OUT, exist_ok=True)
Z = 8
LON0, LON1, LAT0, LAT1 = 27.0, 48.0, 28.0, 42.5          # base map extent
UA = {"User-Agent": "syria-stickman-video/1.0"}


def tilexy(lon, lat, z=Z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def get(url, tries=4):
    import time
    for a in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception as e:
            err = e; time.sleep(1.5 * (a + 1))
    raise err


# ---------------------------------------------------------------- boundaries
for lvl in ("ADM1", "ADM2"):
    p = os.path.join(OUT, f"syr_{lvl}.geojson")
    if not os.path.exists(p):
        url = f"https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/SYR/{lvl}/geoBoundaries-SYR-{lvl}_simplified.geojson"
        open(p, "wb").write(get(url))
    d = json.load(open(p, encoding="utf-8"))
    print(lvl, len(d["features"]), "features")

# ---------------------------------------------------------------- terrain
x0f, y0f = tilexy(LON0, LAT1); x1f, y1f = tilexy(LON1, LAT0)
tx0, tx1, ty0, ty1 = int(x0f), int(x1f), int(y0f), int(y1f)
print("tiles", tx1 - tx0 + 1, "x", ty1 - ty0 + 1)
W = (tx1 - tx0 + 1) * 256; H = (ty1 - ty0 + 1) * 256
elev = np.zeros((H, W), np.float32)


def load(t):
    x, y = t
    b = get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png")
    a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float32)
    return x, y, a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


with ThreadPoolExecutor(16) as ex:
    for x, y, e in ex.map(load, [(x, y) for x in range(tx0, tx1 + 1) for y in range(ty0, ty1 + 1)]):
        elev[(y - ty0) * 256:(y - ty0 + 1) * 256, (x - tx0) * 256:(x - tx0 + 1) * 256] = e
# crop to the exact extent
cx0, cy0 = int((x0f - tx0) * 256), int((y0f - ty0) * 256)
cx1, cy1 = int((x1f - tx0) * 256), int((y1f - ty0) * 256)
elev = elev[cy0:cy1, cx0:cx1]
np.save(os.path.join(OUT, "elev.npy"), elev.astype(np.float16))
json.dump({"z": Z, "lon0": LON0, "lon1": LON1, "lat0": LAT0, "lat1": LAT1, "w": elev.shape[1], "h": elev.shape[0],
           "x0": x0f, "y0": y0f, "x1": x1f, "y1": y1f}, open(os.path.join(OUT, "meta.json"), "w"))
print("elev", elev.shape, float(elev.min()), float(elev.max()))

if PROBE:
    from shapely.geometry import shape
    # hillshade preview
    gy, gx = np.gradient(elev, 500.0)
    slope = np.pi / 2 - np.arctan(2.5 * np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(315), math.radians(40)
    hs = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    img = Image.fromarray((np.clip(hs, 0, 1) * 255).astype(np.uint8)).convert("RGB")
    def px(lon, lat):
        x, y = tilexy(lon, lat)
        return ((x - x0f) * 256, (y - y0f) * 256)
    d = ImageDraw.Draw(img); f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    lines = []
    adm1 = json.load(open(os.path.join(OUT, "syr_ADM1.geojson"), encoding="utf-8"))
    adm2 = json.load(open(os.path.join(OUT, "syr_ADM2.geojson"), encoding="utf-8"))
    for lvl, data, col in (("ADM2", adm2, (255, 80, 60)), ("ADM1", adm1, (60, 160, 255))):
        for ft in data["features"]:
            g = shape(ft["geometry"]); nm = ft["properties"].get("shapeName")
            c = g.representative_point()
            lines.append(f"{lvl}\t{nm}\t{c.x:.3f}\t{c.y:.3f}")
            polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
            for p in polys:
                d.line([px(*q) for q in p.exterior.coords], fill=col, width=2 if lvl == "ADM1" else 1)
            if lvl == "ADM1" or True:
                d.text(px(c.x, c.y), nm, fill=(255, 255, 0) if lvl == "ADM1" else (255, 255, 255), font=f, anchor="mm")
    open(os.path.join(OUT, "names.tsv"), "w", encoding="utf-8").write("\n".join(lines))
    l, t = px(33.5, 37.8); r, b = px(43.5, 32.0)
    img.crop((int(l), int(t), int(r), int(b))).save(os.path.join(OUT, "probe.jpg"), quality=85)
    img.resize((img.width // 3, img.height // 3)).save(os.path.join(OUT, "relief_small.jpg"), quality=80)
