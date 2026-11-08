"""Map rendering: countries, approximate control zones per era, markers, flows."""
import json, math, os
from PIL import ImageDraw, Image
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from textutil import S, font, draw_text, text_w
import relief as R
import numpy as np

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
ADM1 = R.admin_geoms("ADM1"); ADM2 = R.admin_geoms("ADM2")
if ADM1:
    SYRIA_GEOM = unary_union(list(ADM1.values())).buffer(0.003).buffer(-0.003)

LABELS = [  # (text, lon, lat, max_span)
    ("تركيا", 35.2, 38.6, 24), ("العراق", 43.4, 33.6, 14), ("الأردن", 37.3, 31.0, 12),
    ("لبنان", 35.75, 34.0, 4.5), ("البحر المتوسط", 34.4, 34.3, 14), ("اليونان", 22.5, 39.5, 30),
]

B = box
def U(*g): return unary_union(g)

def Dz(*names):
    """Union of real ADM2 districts (falls back to nothing if the geo data is missing)."""
    missing = [n for n in names if n not in ADM2]
    if ADM2 and missing:
        raise KeyError(f"unknown districts: {missing}")
    return U(*[ADM2[n] for n in names if n in ADM2]) if ADM2 else Polygon()

def clip(g): return g.intersection(SYRIA_GEOM)

# approximate sub-district cut lines (lon_min, lat_min, lon_max, lat_max)
aleppo_city = B(37.04, 36.12, 37.24, 36.28)
w_rural_aleppo = B(36.35, 35.95, 37.0, 36.5)
idlib_east = B(36.75, 35.6, 37.6, 36.2)
hajin = B(40.65, 34.3, 41.6, 35.0)
# east of the Euphrates (Raqqa -> Deir ez-Zor -> Abu Kamal), the old SDF / regime dividing line
east_euph = Polygon([(39.7, 36.3), (39.95, 35.75), (40.17, 35.33), (40.46, 35.0), (40.9, 34.45), (41.4, 34.1),
                     (42.6, 34.2), (42.6, 37.6), (39.7, 37.6)])

D = dict(
    dam=("Damascus",), qatana=("Qatana",),
    ghouta=("Rural Damascus", "Duma", "Darayya", "Az-Zabdani"), qalamoun=("Al Qutayfah", "An Nabk", "Yabroud", "At Tall"),
    homs=("Homs", "Al-Qusayr", "Tall Kalakh"), rastan=("Ar-Rastan",), palmyra=("Tadmor", "Al Makhrim"),
    hama=("Hama", "As-Suqaylabiyah", "As-Salamiyeh", "Masyaf", "Muhradah"),
    coast=("Lattakia", "Jablah", "Al-Haffa", "Al-Qardaha", "Tartous", "Banyas", "Safita", "Dreikish", "Sheikh Badr"),
    suwayda=("As-Sweida", "Salkhad", "Shahba"),
    daraa=("Dar'a", "Izra'"), sanamayn=("As-Sanamayn",), quneitra=("Quneitra", "Al Fiq"),
    idlib=("Idleb", "Harim", "Jisr-Ash-Shugur", "Ariha"), maara=("Al Ma'ra",),
    jebel=("Jebel Saman",), safira=("As-Safira",),
    azaz=("A'zaz",), albab=("Al Bab",), jarablus=("Jarablus",), menbij=("Menbij",),
    afrin=("Afrin",), kobani=("Ain Al Arab",), tabqa=("Ath-Thawrah",), raqqa=("Ar-Raqqa",),
    tellabiad=("Tell Abiad",), rasalain=("Ras Al Ain",),
    hasakah=("Al-Hasakeh", "Quamishli", "Al-Malikeyyeh"), dez=("Deir-ez-Zor", "Al Mayadin", "Abu Kamal"),
)
def Z(*keys):
    return U(*[Dz(*D[k]) for k in keys])

def era_zones(era):
    z = {}
    if era == "2013":
        sdf = Z("afrin", "kobani", "hasakah", "rasalain")
        opp = U(Z("ghouta", "idlib", "maara", "azaz", "albab", "jarablus", "menbij", "safira", "raqqa", "tabqa", "dez",
                  "daraa", "quneitra", "rastan", "jebel"), Dz("Al Qutayfah", "An Nabk", "Yabroud")).difference(aleppo_city)
        reg = SYRIA_GEOM.difference(U(sdf, opp))
        z = {"regime": reg, "opp": opp, "sdf": sdf}
    elif era == "2015":
        sdf = Z("afrin", "kobani", "hasakah", "rasalain", "tellabiad")
        isis = Z("raqqa", "tabqa", "dez", "palmyra", "albab", "jarablus", "menbij", "safira")
        opp = U(Z("ghouta", "idlib", "maara", "azaz", "jebel", "daraa", "quneitra", "rastan")).difference(aleppo_city).difference(isis)
        reg = SYRIA_GEOM.difference(U(sdf, isis, opp))
        z = {"regime": reg, "opp": opp, "sdf": sdf, "isis": isis}
    elif era == "2018":
        tr = Z("afrin", "azaz", "albab", "jarablus")
        pocket = hajin.intersection(Z("dez")).intersection(east_euph)
        sdf = U(Z("raqqa", "tabqa", "menbij", "kobani", "hasakah", "rasalain", "tellabiad"),
                Z("dez").intersection(east_euph)).difference(pocket)
        opp = U(Z("idlib", "maara"), Z("jebel").intersection(w_rural_aleppo))
        reg = SYRIA_GEOM.difference(U(tr, sdf, opp, pocket))
        z = {"regime": reg, "opp": opp, "sdf": sdf, "isis": pocket, "tr": tr}
    elif era == "2020":
        tr = Z("afrin", "azaz", "albab", "jarablus", "tellabiad", "rasalain")
        opp = U(Z("idlib", "maara")).difference(idlib_east).difference(Dz("Al Ma'ra"))
        sdf = U(Z("raqqa", "tabqa", "menbij", "kobani", "hasakah"), Z("dez").intersection(east_euph))
        reg = SYRIA_GEOM.difference(U(tr, sdf, opp))
        z = {"regime": reg, "opp": opp, "sdf": sdf, "tr": tr}
    elif era == "dec2024":
        sdf = U(Z("raqqa", "tabqa", "kobani", "hasakah"), Z("dez").intersection(east_euph))
        z = {"gov": SYRIA_GEOM.difference(sdf), "sdf": sdf}
    elif era == "2026":
        sdf = Z("hasakah", "kobani")
        loc = Z("suwayda")
        z = {"gov": SYRIA_GEOM.difference(U(sdf, loc)), "sdf": sdf, "local": loc}
    # close hairline gaps between neighbouring districts of the simplified boundaries
    z = {k: clip(v.buffer(0.004).buffer(-0.004)) for k, v in z.items()}
    return {k: v for k, v in z.items() if not v.is_empty}

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

_ring_cache = {}
def _poly_pts(geom):
    """[(exterior ndarray[lon, mercator-y], [holes...])] cached per geometry object."""
    key = id(geom)
    if key not in _ring_cache:
        def arr(coords):
            a = np.asarray(coords, dtype=np.float64)
            return np.column_stack([a[:, 0], [mercy(la) for la in a[:, 1]]])
        gs = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
        _ring_cache[key] = (geom, [(arr(g.exterior.coords), [arr(i.coords) for i in g.interiors]) for g in gs])
    return _ring_cache[key][1]

def _proj(v, a):
    xs = v.w / 2 + (a[:, 0] - v.lon) * v.k
    ys = v.h / 2 - (a[:, 1] - v.cy) * v.ky
    return list(map(tuple, np.column_stack([xs, ys]).tolist()))

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

    for c in COUNTRIES:                          # flat fallback / outside the terrain extent
        is_sy = c["name"] == "Syria"
        for ring in c["rings"]:
            pts = [v.xy(lo, la) for lo, la in ring]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if max(xs) < -50 or min(xs) > w + 50 or max(ys) < -50 or min(ys) > h + 50:
                continue
            d.polygon(pts, fill=SYRIA if is_sy else LAND, outline=LAND_LINE if not is_sy else (90, 80, 60))
    has_relief = R.blit(panel, view_d, w, h)
    d = ImageDraw.Draw(panel)
    for c in COUNTRIES:                          # neighbour borders on top of the relief
        if c["name"] == "Syria":
            continue
        for ring in c["rings"]:
            pts = [v.xy(lo, la) for lo, la in ring]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if max(xs) < -50 or min(xs) > w + 50 or max(ys) < -50 or min(ys) > h + 50:
                continue
            d.line(pts + [pts[0]], fill=(150, 138, 112), width=max(1, int(1.1 * S)))

    # control zones with crossfade: one mask per zone, blended straight onto the panel
    for era, weight in ((era_prev, 1 - zk), (era_cur, zk)):
        if era in (None, "none") or weight <= 0.01:
            continue
        for name, geom in zones(era).items():
            col = ZONE_STYLE[name][0]
            m = Image.new("L", (w, h), 0); md = ImageDraw.Draw(m)
            for ext, holes in _poly_pts(geom):
                md.polygon(_proj(v, ext), fill=255)
                for hole in holes:
                    md.polygon(_proj(v, hole), fill=0)
            m = m.point(lambda a, k=int(150 * weight): a * k // 255)
            panel.paste(col, (0, 0), m)
            edge = tuple(int(c * 0.55) for c in col)
            ed = ImageDraw.Draw(panel)
            for ext, _h in _poly_pts(geom):
                ed.line(_proj(v, ext), fill=edge, width=max(1, int(1.4 * S * weight)))
    d = ImageDraw.Draw(panel)

    # governorate lines (real ADM1) + Syria's outline
    if ADM1 and view_d["span"] <= 13:
        for g in ADM1.values():
            for ext, _h in _poly_pts(g):
                d.line(_proj(v, ext), fill=(250, 246, 236), width=max(1, int(0.9 * S)))
    for ext, _h in _poly_pts(SYRIA_GEOM):
        d.line(_proj(v, ext), fill=(70, 60, 45), width=max(2, int(1.8 * S)))

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
