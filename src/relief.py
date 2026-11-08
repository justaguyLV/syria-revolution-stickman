"""Real-terrain base map.

Reads the elevation grid + admin boundaries produced by tools/fetch_geo.py (AWS Terrarium tiles, z8, web-mercator)
and renders a hillshaded, hypsometric-tinted relief once. `blit()` then crops/scales it for any map view.
If the geo data is missing, everything degrades to the old flat map (blit returns False).
"""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = os.environ.get("GEO_DIR") or os.path.join(ROOT, "build_tmp", "geo")
N = 256 * 2 ** 8                       # global mercator pixels at z8
WASH = np.array([238, 232, 216], np.float32)
SS = 2                                 # supersampling for the land masks

_state = {"ok": False}
_cache = {}


def mercy(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _gpx(lon, lat):                    # lon/lat -> global z8 pixel
    return (lon + 180) / 360 * N, (1 - mercy(lat) / math.pi) / 2 * N


def _load_elev():
    npy, npz = os.path.join(GEO, "elev.npy"), os.path.join(GEO, "elev.npz")
    if os.path.exists(npy):
        return np.load(npy).astype(np.float32)
    return np.load(npz)["e"].astype(np.float32)


def _geojson(lvl):
    p = os.path.join(GEO, f"syr_{lvl}.geojson")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def admin_geoms(lvl):
    """{name: shapely geometry} for ADM1 / ADM2 (empty dict when data is missing)."""
    d = _geojson(lvl)
    return {} if d is None else {f["properties"]["shapeName"]: shape(f["geometry"]).buffer(0) for f in d["features"]}


def _tint(e):
    stops = [(-500, (160, 175, 150)), (0, (186, 204, 158)), (150, (206, 210, 160)), (400, (226, 214, 168)),
             (700, (222, 200, 152)), (1100, (196, 170, 128)), (1600, (170, 142, 108)), (2200, (150, 124, 98)),
             (3000, (205, 198, 190)), (4000, (240, 238, 235))]
    xs = [s[0] for s in stops]
    return np.stack([np.interp(e, xs, [s[1][c] for s in stops]) for c in range(3)], -1).astype(np.float32)


def _hillshade(e, y0g):
    H, W = e.shape
    k = np.ones((3, 3), np.float32) / 9
    p = np.pad(e, 1, mode="edge")
    es = sum(p[i:i + H, j:j + W] for i in range(3) for j in range(3)) / 9      # light smoothing of tile noise
    rows = y0g + np.arange(H)
    lat = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * rows / N))))
    cell = (40075016.686 / N * np.cos(np.radians(lat)))[:, None]
    gy, gx = np.gradient(es)
    gx, gy = gx / cell, gy / cell
    z = 2.2                                                                      # vertical exaggeration
    slope = np.arctan(z * np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    out = 0
    for az, alt, wt in ((315, 42, 0.75), (20, 55, 0.25)):
        a, l = math.radians(az), math.radians(alt)
        out = out + wt * (np.sin(l) * np.cos(slope) + np.cos(l) * np.sin(slope) * np.cos(a - aspect))
    return out / (0.75 * math.sin(math.radians(42)) + 0.25 * math.sin(math.radians(55)))   # flat ground == 1.0


def _poly_mask(polys, W, H, x0g, y0g):
    m = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(m)
    for ring_list in polys:                       # [(exterior, [holes])]
        ext, holes = ring_list
        d.polygon([((gx - x0g) * SS, (gy - y0g) * SS) for gx, gy in (_gpx(*q) for q in ext)], fill=255)
        for h in holes:
            d.polygon([((gx - x0g) * SS, (gy - y0g) * SS) for gx, gy in (_gpx(*q) for q in h)], fill=0)
    return m.resize((W, H), Image.BOX)


def _polys_of(geom):
    gs = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    return [(list(g.exterior.coords), [list(i.coords) for i in g.interiors]) for g in gs]


def load():
    """Build the relief base. Safe to call repeatedly; call it before forking worker processes."""
    if _state["ok"] or _state.get("failed"):
        return _state["ok"]
    try:
        meta = json.load(open(os.path.join(GEO, "meta.json")))
        e = _load_elev()
        H, W = e.shape
        x0g, y0g = meta["x0"] * 256, meta["y0"] * 256
        shade = np.clip(_hillshade(e, y0g), 0.25, 1.6)
        rgb = np.clip(_tint(e) * (shade[..., None] ** 0.95) * 1.02, 0, 255)

        # land mask (all countries) + Syria mask (ADM1 union) -> mute the neighbours so Syria pops
        countries = json.load(open(os.path.join(ROOT, "data", "countries.json"), encoding="utf-8"))
        land = []
        for c in countries:
            for r in c["rings"]:
                land.append((r, []))
        land_m = _poly_mask(land, W, H, x0g, y0g)
        adm1 = admin_geoms("ADM1")
        if adm1:
            syr = unary_union(list(adm1.values())).buffer(0)
            syr_m = np.asarray(_poly_mask(_polys_of(syr), W, H, x0g, y0g), np.float32)[..., None] / 255
            rgb = rgb * (1 - 0.5 * (1 - syr_m)) + WASH * 0.5 * (1 - syr_m)
        _state.update(ok=True, rgb=Image.fromarray(rgb.astype(np.uint8)), land=land_m, W=W, H=H, x0g=x0g, y0g=y0g)
    except Exception as ex:                       # no geo data -> flat fallback
        print("relief disabled:", repr(ex))
        _state["failed"] = True
    return _state["ok"]


def blit(panel, view_d, w, h):
    """Paste the relief (land only) into `panel` (RGB, w x h) for view {lon, lat, span}. Returns False if unavailable."""
    if not load():
        return False
    st = _state
    key = (round(view_d["lon"], 3), round(view_d["lat"], 3), round(view_d["span"], 3), w, h)
    if key in _cache:
        rgb, mask, pos = _cache[key]
    else:
        scale = N / 360.0
        k = w / view_d["span"]                    # output px per degree lon
        cx, cy = _gpx(view_d["lon"], view_d["lat"])
        cx -= st["x0g"]; cy -= st["y0g"]
        hw, hh = w / k * scale / 2, h / k * scale / 2
        sx0, sy0, sx1, sy1 = cx - hw, cy - hh, cx + hw, cy + hh
        ix0, iy0, ix1, iy1 = max(sx0, 0), max(sy0, 0), min(sx1, st["W"]), min(sy1, st["H"])
        if ix1 - ix0 < 2 or iy1 - iy0 < 2:
            return False
        fx, fy = w / (sx1 - sx0), h / (sy1 - sy0)
        dx0, dy0 = int(round((ix0 - sx0) * fx)), int(round((iy0 - sy0) * fy))
        dx1, dy1 = int(round((ix1 - sx0) * fx)), int(round((iy1 - sy0) * fy))
        size = (max(1, dx1 - dx0), max(1, dy1 - dy0))
        box = (ix0, iy0, ix1, iy1)
        rgb = st["rgb"].resize(size, Image.BILINEAR, box=box)
        mask = st["land"].resize(size, Image.BILINEAR, box=box)
        pos = (dx0, dy0)
        if len(_cache) > 6:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (rgb, mask, pos)
    panel.paste(rgb, pos, mask)
    return True
