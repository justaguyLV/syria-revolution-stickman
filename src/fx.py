"""On-screen effects driven by the same per-scene events as the sound (data/sfx.json).

Times are scene-relative seconds (`lt`). Everything draws with RGBA patches so glows/smoke blend naturally.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from textutil import S, font, draw_text, text_w

BLASTS = ("blast", "shell")


def events(sc, *types):
    return [e for e in sc.get("events", []) if e["type"] in types]


# ------------------------------------------------------------------ global shake / flash
def shake(sc, lt):
    """(dx, dy) in design px for the stage + a 0..1 flash strength."""
    amp = 0.0; fl = 0.0
    for e in sc.get("events", []):
        a = lt - e["t"]
        if e["type"] in BLASTS and 0 <= a < 1.3 and not e.get("dist"):
            k = e.get("size", 1.0)
            amp += 7 * k * math.exp(-a * 3.2)
            fl = max(fl, 0.5 * k * math.exp(-a * 14) if a < 0.3 else 0.0)
        elif e["type"] == "rumble" and 0 <= a < e.get("dur", 8):
            fade = min(1.0, a / 1.2, (e.get("dur", 8) - a) / 1.5)
            amp += 4.5 * max(0.0, fade)
    if amp <= 0.05:
        return 0.0, 0.0, fl
    r = random.Random(int(lt * 60))
    return r.uniform(-amp, amp), r.uniform(-amp, amp) * 0.7, min(0.55, fl)


def shots(sc, who, lt):
    """(flash 0..1, recoil 0..1) for the shooter `who` at scene time lt."""
    flash = 0.0; rec = 0.0
    for e in sc.get("events", []):
        if e["type"] != "shot" or e.get("who", "*") not in ("*", who):
            continue
        gap = e.get("gap", 0.1)
        n = e.get("n", 3)
        a = lt - e["t"]
        if -0.01 <= a < n * gap + 0.05:
            ph = (a % gap) / gap if gap else 0
            if int(max(a, 0) / gap) < n:
                flash = max(flash, max(0.0, 1.0 - ph * 3.2))
                rec = max(rec, max(0.0, 1.0 - ph * 2.0))
    return flash, rec


def falling(sc, who, lt):
    """progress 0..1 of a fall triggered by a 'fall' event for `who` (None if not falling)."""
    for e in sc.get("events", []):
        if e["type"] == "fall" and e.get("who") == who and lt >= e["t"]:
            return min(1.0, (lt - e["t"]) / 0.9)
    return None


def chant_now(sc, lt):
    """-> (text, pulse 0..1) for the chant bubble currently being shouted, else None."""
    for e in sc.get("events", []):
        if e["type"] != "chant":
            continue
        per = e.get("period", 1.9)
        n = e.get("reps", 3)
        a = lt - e["t"]
        if 0 <= a < per * n:
            ph = (a % per) / per
            return e.get("text") or "", (1 - ph) ** 1.5 if ph < 0.65 else 0.0
    return None


# ------------------------------------------------------------------ glow / fireball patches
_grad_cache = {}
def _radial(size):
    if size not in _grad_cache:
        y, x = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
        _grad_cache[size] = np.sqrt(x * x + y * y) / size
    return _grad_cache[size]


def _blob(r, stops, alpha_fn):
    """RGBA patch (2r+1)^2: colour via stops [(pos, (r,g,b)), ...], alpha via alpha_fn(dist 0..1)."""
    r = max(2, int(r))
    dist = np.minimum(_radial(r), 1.0)
    pos = [p for p, _ in stops]
    chans = [np.interp(dist, pos, [c[i] for _, c in stops]) for i in range(3)]
    a = np.clip(alpha_fn(dist), 0, 1) * (_radial(r) <= 1)
    arr = np.stack(chans + [a * 255], axis=-1).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _paste(img, patch, cx, cy):
    x0, y0 = int(cx - patch.width / 2), int(cy - patch.height / 2)
    if x0 > img.width or y0 > img.height or x0 + patch.width < 0 or y0 + patch.height < 0:
        return
    img.alpha_composite(patch, (max(0, x0), max(0, y0)), (max(0, -x0), max(0, -y0), patch.width, patch.height)) \
        if img.mode == "RGBA" else img.paste(patch.convert("RGB"), (x0, y0), patch.split()[3])


def fireball(img, cx, cy, age, size_px, seed=0):
    """Expanding fireball + shockwave + rising smoke + scorch mark.  size_px in output pixels (already * S)."""
    rnd = random.Random(seed)
    if age < 0:
        return
    if age > 0.8:                                             # scorch mark stays
        _paste(img, _blob(size_px * 0.5, [(0, (40, 30, 24)), (1, (60, 50, 40))], lambda d: 0.42 * (1 - d) ** 0.6), cx, cy + size_px * 0.05)
    if age < 1.5:                                             # shockwave ring
        rr = size_px * (0.3 + 2.6 * (1 - math.exp(-age * 3.5)))
        ring = _blob(rr, [(0, (255, 255, 255)), (1, (255, 240, 210))], lambda d: np.exp(-((d - 0.93) / 0.045) ** 2) * 0.55 * max(0, 1 - age / 1.5))
        _paste(img, ring, cx, cy)
    for k in range(7):                                        # smoke plume
        t0 = 0.12 + k * 0.1
        a = age - t0
        if a < 0 or a > 5.5:
            continue
        rise = size_px * (0.2 + 0.55 * a) * (0.7 + 0.3 * rnd.random())
        drift = rnd.uniform(-0.5, 0.5) * size_px * 0.3 * a
        rad = size_px * (0.35 + 0.22 * a) * rnd.uniform(0.8, 1.2)
        fade = max(0.0, 1 - a / 5.5)
        g = int(55 + 35 * (a / 5.5))
        _paste(img, _blob(rad, [(0, (g, g, g)), (1, (g + 25, g + 25, g + 25))], lambda d, f=fade: 0.46 * f * (1 - d) ** 0.9), cx + drift, cy - rise)
    if age < 0.9:                                             # fire core
        e = 1 - math.exp(-age * 7)
        rad = size_px * (0.35 + 1.0 * e)
        glow = max(0.0, 1 - age / 0.9)
        stops = [(0, (255, 255, 235)), (0.35, (255, 205, 80)), (0.7, (240, 100, 30)), (1, (120, 30, 20))]
        _paste(img, _blob(rad * 1.5, [(0, (255, 160, 60)), (1, (255, 90, 20))], lambda d, g=glow: 0.32 * g * (1 - d) ** 1.4), cx, cy)
        _paste(img, _blob(rad, stops, lambda d, g=glow: g * (1 - d ** 3)), cx, cy)
    if age < 0.35:                                            # flying sparks
        ds = ImageDraw.Draw(img)
        for i in range(14):
            ang = rnd.uniform(0, math.tau); sp = rnd.uniform(0.8, 2.2) * size_px
            r0 = sp * (1 - math.exp(-age * 9)) * 0.55
            x, y = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang) - 0.2 * size_px * age
            ds.ellipse([x - 1.5 * S, y - 1.5 * S, x + 1.5 * S, y + 1.5 * S], fill=(255, 220, 120, int(255 * (1 - age / 0.35))))


def sparks(img, cx, cy, lt, rate=14, spread=18, seed=0):
    """Gunfight flicker: little muzzle sparks around a point."""
    ds = ImageDraw.Draw(img)
    for i in range(5):
        rnd = random.Random(seed * 100 + int(lt * rate) * 7 + i)
        if rnd.random() < 0.55:
            continue
        x = cx + rnd.uniform(-spread, spread) * S; y = cy + rnd.uniform(-spread, spread) * S
        ang = rnd.uniform(0, math.tau); ln = rnd.uniform(4, 9) * S
        ds.line([x, y, x + ln * math.cos(ang), y + ln * math.sin(ang)], fill=(255, 224, 120, 255), width=max(1, int(1.6 * S)))
        _paste(img, _blob(4 * S, [(0, (255, 250, 200)), (1, (255, 170, 60))], lambda d: (1 - d) ** 1.2), x, y)


def map_fx(panel, v, sc, lt):
    """Draw every active blast / gunfight of the scene on the map panel (RGB panel; v = mapview.View)."""
    evs = [(i, e) for i, e in enumerate(sc.get("events", [])) if "lon" in e]
    if not evs:
        return panel
    layer = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    for i, e in evs:
        x, y = v.xy(e["lon"], e["lat"])
        if e["type"] in BLASTS:
            fireball(layer, x, y, lt - e["t"], 24 * S * e.get("size", 1.0) ** 0.6, seed=i)
        elif e["type"] == "shot":
            dur = e.get("n", 3) * e.get("gap", 0.1) + 0.9 if e.get("sparks", True) else 0
            if 0 <= lt - e["t"] < dur + 1.4:
                sparks(layer, x, y, lt, seed=i)
                if lt - e["t"] > dur:
                    pass
    out = panel.convert("RGBA")
    out.alpha_composite(layer)
    panel.paste(out.convert("RGB"))
    return panel


# ------------------------------------------------------------------ stage helpers
def bubble(d, x, y, text, pulse, w=None):
    """Speech bubble with Arabic text popping with the rhythm of the chant."""
    f = font(20 + 4 * pulse)
    tw = text_w(d, text, f) / S
    w = tw + 28
    sc_ = 1.0 + 0.07 * pulse
    h = 40 * sc_
    x0, x1 = x - w * sc_ / 2, x + w * sc_ / 2
    d.rounded_rectangle([x0 * S, (y - h / 2) * S, x1 * S, (y + h / 2) * S], radius=14 * S, fill=(255, 255, 255), outline=(30, 30, 36), width=int(2.4 * S))
    d.polygon([((x - 9) * S, (y + h / 2 - 1) * S), ((x + 9) * S, (y + h / 2 - 1) * S), ((x + 2) * S, (y + h / 2 + 13) * S)], fill=(255, 255, 255), outline=(30, 30, 36))
    d.line([((x - 8) * S, (y + h / 2) * S), ((x + 8) * S, (y + h / 2) * S)], fill=(255, 255, 255), width=int(3 * S))
    draw_text(d, (x * S, y * S), text, f, (192, 57, 43), "mm")


def fx_firework(img, cx, cy, age, col, size=70):
    """Radial firework burst (stage canvas RGBA, px already * S)."""
    if age < 0 or age > 1.8:
        return
    ds = ImageDraw.Draw(img)
    e = 1 - math.exp(-age * 3.2)
    fade = max(0.0, 1 - age / 1.8)
    for i in range(26):
        a = i / 26 * math.tau
        r0 = size * S * e * (0.65 + 0.35 * ((i * 7) % 5) / 4)
        x, y = cx + r0 * math.cos(a), cy + r0 * math.sin(a) + 18 * S * age * age
        tail = 0.82
        x2, y2 = cx + r0 * tail * math.cos(a), cy + r0 * tail * math.sin(a) + 18 * S * age * age * tail
        c = (*col, int(255 * fade))
        ds.line([x2, y2, x, y], fill=c, width=max(1, int(2.2 * S)))
        ds.ellipse([x - 2 * S, y - 2 * S, x + 2 * S, y + 2 * S], fill=c)
    _paste(img, _blob(size * S * 0.9, [(0, col), (1, col)], lambda d: 0.16 * fade * (1 - d) ** 1.5), cx, cy)
