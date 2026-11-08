"""Map rendering: countries, approximate control zones per era, markers, flows."""
import json, math, os
from PIL import ImageDraw, Image
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from textutil import S, font, draw_text, text_w

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SEA = (200, 225, 240)
LAND = (228, 220, 200)
LAND_LINE = (160, 148, 120)
SYRIA = (246, 238, 214)
INK = (30, 30, 36)

COUNTRIES = json.load(open(os.path.join(ROOT, "data", "countries.json"), encoding="utf-8"))
_syria_polys = []
for c in COUNTRIES:
    if c["name"] == "Syria":
        _syria_polys = [Polygon(r) for r in c["rings"]]
SYRIA_GEOM = unary_union(_syria_polys).buffer(0)

LABELS = [  # (text, lon, lat, max_span)
    ("تركيا", 35.2, 38.6, 24), ("العراق", 43.4, 33.6, 14), ("الأردن", 37.3, 31.0, 12),
    ("لبنان", 35.75, 34.0, 4.5), ("البحر المتوسط", 34.4, 34.3, 14), ("اليونان", 22.5, 39.5, 30),
]

B = box
def U(*g): return unary_union(g)

# approximate regions (lon_min, lat_min, lon_max, lat_max)
west_core = B(35.5, 32.2, 38.4, 35.55)
coast = B(35.5, 34.5, 36.4, 36.0)
idlib = B(36.2, 35.45, 37.0, 36.1)
idlib_small = B(36.0, 35.5, 36.85, 36.25)
afrin = B(36.5, 36.3, 37.15, 36.85)
rural_aleppo_w = B(36.8, 36.0, 37.4, 36.7)
aleppo_area = B(37.0, 36.0, 37.4, 36.4)
bab_jarablus = B(37.2, 36.4, 38.4, 37.1)
kobani = B(38.0, 36.6, 38.9, 37.1)
ne_corner = B(40.0, 36.0, 42.5, 37.5)
tabqa_raqqa = B(38.4, 35.4, 39.6, 36.4)
dez = B(39.6, 34.2, 41.5, 35.8)
jazira = B(38.2, 34.0, 42.5, 37.5)
east_all = B(38.4, 34.0, 42.5, 37.5)
badiya_isis = B(37.5, 33.8, 41.5, 34.8)
south_rebel = B(35.6, 32.3, 36.4, 33.0)
ghouta = B(36.3, 33.4, 36.6, 33.65)
suwayda = B(36.3, 32.4, 37.05, 33.1)
tal_abyad = B(38.7, 36.5, 40.2, 36.95)
hajin = B(40.4, 34.3, 41.3, 35.0)

def clip(g): return g.intersection(SYRIA_GEOM)

def era_zones(era):
    z = {}
    if era == "2013":
        opp = U(idlib, rural_aleppo_w, bab_jarablus, tabqa_raqqa, dez, south_rebel, ghouta)
        sdf = U(afrin, kobani, ne_corner)
        reg = U(west_core, coast, aleppo_area).difference(U(opp, sdf))
        z = {"regime": reg, "opp": opp.difference(sdf), "sdf": sdf}
    elif era == "2015":
        sdf = U(afrin, kobani, ne_corner)
        isis = U(jazira, badiya_isis, bab_jarablus).difference(sdf)
        opp = U(idlib, rural_aleppo_w, south_rebel, ghouta).difference(isis)
        reg = U(west_core, coast, aleppo_area).difference(U(isis, opp, sdf))
        z = {"regime": reg, "opp": opp, "sdf": sdf, "isis": isis}
    elif era == "2018":
        tr = U(bab_jarablus, afrin)
        sdf = east_all.difference(tr).difference(hajin)
        opp = U(idlib, rural_aleppo_w).difference(tr)
        isis = hajin
        reg = SYRIA_GEOM.difference(U(tr, sdf, opp, isis))
        z = {"regime": reg, "opp": opp, "sdf": sdf, "isis": isis, "tr": tr}
    elif era == "2020":
        tr = U(bab_jarablus, afrin, tal_abyad)
        sdf = east_all.difference(tr)
        opp = idlib_small.difference(tr)
        reg = SYRIA_GEOM.difference(U(tr, sdf, opp))
        z = {"regime": reg, "opp": opp, "sdf": sdf, "tr": tr}
    elif era == "dec2024":
        sdf = east_all
        z = {"gov": SYRIA_GEOM.difference(sdf), "sdf": sdf}
    elif era == "2026":
        sdf = U(ne_corner, kobani)
        loc = suwayda
        z = {"gov": SYRIA_GEOM.difference(U(sdf, loc)), "sdf": sdf, "local": loc}
    z = {k: clip(v) for k, v in z.items() if not v.is_empty}
    if era in ("2013", "2015", "2018"):
        rest = SYRIA_GEOM.difference(unary_union(list(z.values())))
        rest = rest.buffer(-0.05).buffer(0.05)
        if not rest.is_empty:
            z["desert"] = rest
    return z

ZONE_STYLE = {
    "regime": ((192, 57, 43), "النظام وحلفاؤه"),
    "opp": ((46, 139, 87), "فصائل المعارضة"),
    "sdf": ((224, 176, 0), "الإدارة الكردية - قسد"),
    "isis": ((60, 60, 66), "تنظيم الدولة"),
    "tr": ((59, 126, 161), "نفوذ تركيا وحلفائها"),
    "gov": ((46, 139, 87), "الحكومة الانتقالية"),
    "local": ((142, 68, 173), "السويداء - إدارة محلية"),
    "desert": ((150, 150, 150), "بادية ومناطق متنازع عليها"),
}

_zone_cache = {}
def zones(era):
    if era not in _zone_cache:
        _zone_cache[era] = era_zones(era)
    return _zone_cache[era]

def _rings(geom):
    polys = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    for p in polys:
        yield list(p.exterior.coords)

def mercy(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

class View:
    def __init__(self, lon, lat, span, w, h):
        self.lon, self.lat, self.span, self.w, self.h = lon, lat, span, w, h
        self.k = w / span                       # px per degree lon
        self.cy = mercy(lat)
        self.ky = self.k * 180 / math.pi        # px per mercator unit
    def xy(self, lon, lat):
        return (self.w / 2 + (lon - self.lon) * self.k, self.h / 2 - (mercy(lat) - self.cy) * self.ky)

def lerp_view(a, b, k):
    k = k * k * (3 - 2 * k)
    la = math.log(a["span"]); lb = math.log(b["span"])
    return {"lon": a["lon"] + (b["lon"] - a["lon"]) * k, "lat": a["lat"] + (b["lat"] - a["lat"]) * k,
            "span": math.exp(la + (lb - la) * k)}

def draw_map(img, box_px, view_d, era_prev, era_cur, zk, scene, lt, dur):
    """Draw map into `img` inside box_px=(x0,y0,x1,y1) (already scaled pixels)."""
    x0, y0, x1, y1 = box_px
    w, h = x1 - x0, y1 - y0
    panel = Image.new("RGB", (w, h), SEA)
    d = ImageDraw.Draw(panel)
    v = View(view_d["lon"], view_d["lat"], view_d["span"], w, h)

    for c in COUNTRIES:
        is_sy = c["name"] == "Syria"
        for ring in c["rings"]:
            pts = [v.xy(lo, la) for lo, la in ring]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if max(xs) < -50 or min(xs) > w + 50 or max(ys) < -50 or min(ys) > h + 50:
                continue
            d.polygon(pts, fill=SYRIA if is_sy else LAND, outline=LAND_LINE if not is_sy else (90, 80, 60))
            if is_sy:
                d.line(pts + [pts[0]], fill=(90, 80, 60), width=max(2, int(1.6 * S)))

    # zones with crossfade
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for era, weight in ((era_prev, 1 - zk), (era_cur, zk)):
        if era in (None, "none") or weight <= 0.01:
            continue
        for name, geom in zones(era).items():
            col = ZONE_STYLE[name][0]
            for ring in _rings(geom):
                pts = [v.xy(lo, la) for lo, la in ring]
                tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                ImageDraw.Draw(tmp).polygon(pts, fill=col + (int(165 * weight),))
                layer = Image.alpha_composite(layer, tmp)
    panel = Image.alpha_composite(panel.convert("RGBA"), layer).convert("RGB")
    d = ImageDraw.Draw(panel)

    # labels
    for text, lo, la, mx in LABELS:
        if view_d["span"] <= mx:
            px, py = v.xy(lo, la)
            draw_text(d, (px, py), text, font(15), (120, 110, 95), "mm")

    # animated flows (refugees)
    for fl in scene.get("flows", []):
        k = min(1.0, max(0.0, (lt - 1.0) / max(1.0, dur * 0.7)))
        a = v.xy(*fl["from"]); b = v.xy(*fl["to"])
        e = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        d.line([a, e], fill=(170, 40, 40), width=int(4 * S))
        ang = math.atan2(e[1] - a[1], e[0] - a[0])
        hd = 12 * S
        d.polygon([e, (e[0] - hd * math.cos(ang - .45), e[1] - hd * math.sin(ang - .45)),
                   (e[0] - hd * math.cos(ang + .45), e[1] - hd * math.sin(ang + .45))], fill=(170, 40, 40))
        if k > 0.9:
            pill_label(d, (b[0], b[1] - 16 * S), fl["label"], 15)

    # animated advance path (offensive)
    path = scene.get("path")
    if path:
        k = min(1.0, max(0.0, (lt - 0.8) / max(1.0, dur - 2.0)))
        pts = [v.xy(p["lon"], p["lat"]) for p in path]
        total = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        run = total * k
        drawn = [pts[0]]; acc = 0
        for i in range(len(pts) - 1):
            seg = math.dist(pts[i], pts[i + 1])
            if acc + seg <= run:
                drawn.append(pts[i + 1]); acc += seg
            else:
                f = (run - acc) / seg if seg else 0
                drawn.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f))
                break
        if len(drawn) > 1:
            d.line(drawn, fill=(46, 139, 87), width=int(6 * S), joint="curve")
        for p, pt in zip(path, pts):
            if k >= p["at"] - 0.02:
                dot(d, pt, 8, (46, 139, 87))
                pill_label(d, (pt[0] + 14 * S, pt[1]), p["name"], 17, anchor="lm")

    # markers
    for i, m in enumerate(scene.get("markers", [])):
        appear = 0.6 + i * 0.35
        if lt < appear:
            continue
        k = min(1.0, (lt - appear) / 0.35)
        px, py = v.xy(m["lon"], m["lat"])
        r = (11 if m.get("big") else 7) * S * (0.3 + 0.7 * k)
        if m.get("ripple"):
            ph = (lt * 0.8) % 1.0
            rr = (14 + 40 * ph) * S
            d.ellipse([px - rr, py - rr, px + rr, py + rr], outline=(192, 57, 43), width=int(3 * S))
        dot(d, (px, py), r / S, (192, 57, 43) if m.get("big") else (60, 60, 70))
        pill_label(d, (px + 12 * S, py - 2 * S), m["name"], 17 if m.get("big") else 15, anchor="lm")

    # legend
    used = []
    for era in (era_cur,):
        if era and era != "none":
            used = list(zones(era).keys())
    if used:
        ly = h - 14 * S - len(used) * 24 * S
        d.rounded_rectangle([12 * S, ly - 8 * S, 250 * S, h - 8 * S], radius=8 * S, fill=(255, 255, 255), outline=(180, 170, 150))
        for i, name in enumerate(used):
            col, lab = ZONE_STYLE[name]
            yy = ly + i * 24 * S + 10 * S
            d.rectangle([22 * S, yy - 8 * S, 40 * S, yy + 8 * S], fill=col)
            draw_text(d, (246 * S, yy), lab, font(14), INK, "rm")
    draw_text(d, (w - 10 * S, h - 10 * S), "خريطة توضيحية تقريبية", font(12), (110, 100, 85), "rd")
    img.paste(panel, (x0, y0))

def dot(d, p, r, col):
    r *= S
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col, outline=(255, 255, 255), width=int(2 * S))

def pill_label(d, p, text, size, anchor="mm"):
    f = font(size)
    tw = text_w(d, text, f)
    pad = 6 * S
    x, y = p
    if anchor == "lm":
        bx0, bx1 = x, x + tw + 2 * pad
    else:
        bx0, bx1 = x - tw / 2 - pad, x + tw / 2 + pad
    hh = size * S * 0.95
    d.rounded_rectangle([bx0, y - hh / 2 - 3 * S, bx1, y + hh / 2 + 3 * S], radius=8 * S, fill=(255, 255, 255), outline=(190, 180, 160))
    draw_text(d, ((bx0 + bx1) / 2, y), text, f, INK, "mm")
