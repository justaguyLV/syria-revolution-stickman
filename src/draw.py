"""Stickman primitives + animated 'stage' scenes (left panel, 420x600 design px).  Figures come from rig.py."""
import math
from textutil import S, font, draw_text, text_w
import rig
import fx

INK = (30, 30, 36)
RED = (192, 57, 43)
GREEN = (46, 139, 87)
YELLOW = (224, 176, 0)
GREY = (90, 90, 98)
PAPER = (247, 241, 227)
GY = 520  # ground line
SOLDIER = (52, 58, 46)
BLUE = (59, 126, 161)
CANVAS = None   # RGBA stage canvas (set by build.py each frame, used for glows / fireballs)


def L(d, pts, w=4, c=INK):
    d.line([(x * S, y * S) for x, y in pts], fill=c, width=max(1, int(w * S)), joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = w * S / 2
        d.ellipse([x * S - r, y * S - r, x * S + r, y * S + r], fill=c)

def C(d, x, y, r, fill=None, outline=None, w=2):
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill, outline=outline, width=int(w * S))

def R(d, x0, y0, x1, y1, fill=None, outline=None, w=2, rad=0):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=rad * S, fill=fill, outline=outline, width=int(w * S))

def P(d, pts, fill=None, outline=None, w=2):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=outline)

def T(d, xy, text, size, fill=INK, anchor="mm"):
    draw_text(d, (xy[0] * S, xy[1] * S), text, font(size), fill, anchor)


def person(d, x, gy, h, t, pose="stand", color=INK, sign=None, ph=0.0, flip=1, head_fill=PAPER, **kw):
    """Stickman of total height h standing with its feet on gy."""
    return rig.figure(d, x, gy, h, t, pose, color=color, head_fill=head_fill, flip=flip, ph=ph, sign=sign, **kw)


def soldier(d, x, gy, h, t, sc, lt, who, flip=-1, ph=0.0, pose="aim", color=SOLDIER, **kw):
    fl, rc = fx.shots(sc, who, lt)
    return person(d, x, gy, h, t, pose, color, ph=ph, flip=flip, helmet=True, prop="rifle", flash=fl, recoil=rc, **kw)


def skyline(d, y=GY, col=(233, 225, 206), seed=3):
    """Old-city silhouette (domes + minarets) behind the action."""
    import random
    r = random.Random(seed); x = -10
    while x < 430:
        w = r.choice([34, 44, 56]); hh = r.choice([46, 62, 80, 54])
        R(d, x, y - hh, x + w, y, fill=col)
        k = r.random()
        if k < 0.3:      # dome
            d.pieslice([(x + w * 0.12) * S, (y - hh - w * 0.38) * S, (x + w * 0.88) * S, (y - hh + w * 0.38) * S], 180, 360, fill=col)
        elif k < 0.55:   # minaret
            R(d, x + w * 0.4, y - hh - 40, x + w * 0.6, y - hh, fill=col)
            P(d, [(x + w * 0.36, y - hh - 40), (x + w * 0.64, y - hh - 40), (x + w * 0.5, y - hh - 58)], fill=col)
        x += w + r.choice([2, 5, 9])


def crowd_back(d, t, items):
    for it in items:
        person(d, **it)


def tank(d, x, gy, w, t):
    c = (86, 98, 74)
    R(d, x - w / 2, gy - w * 0.14, x + w / 2, gy, fill=(60, 60, 60), rad=w * 0.07)
    for i in range(5):
        C(d, x - w * 0.4 + i * w * 0.2, gy - w * 0.07, w * 0.045, fill=(150, 150, 150))
    R(d, x - w * 0.4, gy - w * 0.3, x + w * 0.4, gy - w * 0.13, fill=c, outline=INK, w=2, rad=4)
    R(d, x - w * 0.18, gy - w * 0.44, x + w * 0.18, gy - w * 0.28, fill=c, outline=INK, w=2, rad=4)
    L(d, [(x - w * 0.18, gy - w * 0.37), (x - w * 0.62, gy - w * 0.39 - 2 * math.sin(t * 5))], 5, INK)


def jet(d, x, y, w, color=GREY):
    P(d, [(x - w / 2, y), (x - w * 0.1, y - w * 0.08), (x + w * 0.4, y - w * 0.05), (x + w / 2, y + w * 0.02),
          (x + w * 0.1, y + w * 0.09), (x - w * 0.4, y + w * 0.05)], fill=color, outline=INK)
    P(d, [(x - w * 0.05, y), (x + w * 0.15, y), (x - w * 0.15, y - w * 0.22)], fill=(110, 110, 118), outline=INK)
    P(d, [(x - w * 0.42, y), (x - w * 0.5, y - w * 0.12), (x - w * 0.34, y - w * 0.04)], fill=color, outline=INK)


def waves(d, y, x0, x1, t, color=(110, 160, 200)):
    pts = [(x, y + 5 * math.sin(x / 18 + t * 2)) for x in range(int(x0), int(x1), 6)]
    L(d, pts, 3, color)


def boat(d, x, y, w, t, n=4):
    y += 4 * math.sin(t * 2 + x)
    for i in range(n):
        person(d, x - w * 0.32 + i * w * 0.2, y - 6, 52, t, "sad", INK)
    P(d, [(x - w / 2, y - 8), (x + w / 2, y - 8), (x + w * 0.38, y + 14), (x - w * 0.38, y + 14)], fill=(150, 100, 60), outline=INK)


def cloud(d, x, y, r, t, col=(150, 170, 100)):
    for i, (dx, dy, k) in enumerate([(0, 0, 1), (-.8, .3, .75), (.8, .25, .8), (-.3, -.6, .7), (.45, -.55, .65)]):
        rr = r * k * (1 + 0.06 * math.sin(t * 2 + i))
        C(d, x + dx * r, y + dy * r, rr, fill=col + (), outline=(110, 130, 70), w=1.5)


def building(d, x, gy, w, h, shake=0.0, damaged=False, color=(205, 195, 170)):
    x += shake
    if damaged:
        P(d, [(x - w / 2, gy), (x - w / 2, gy - h), (x - w * 0.1, gy - h), (x + w * 0.05, gy - h * 0.7), (x + w * 0.2, gy - h * 0.85),
              (x + w / 2, gy - h * 0.55), (x + w / 2, gy)], fill=color, outline=INK)
    else:
        R(d, x - w / 2, gy - h, x + w / 2, gy, fill=color, outline=INK, w=2)
    for r_ in range(int(h // 34)):
        for c_ in range(2):
            wx = x - w * 0.27 + c_ * w * 0.4
            wy = gy - h + 12 + r_ * 30
            if damaged and wy < gy - h * 0.55 and c_ == 1:
                continue
            R(d, wx, wy, wx + w * 0.17, wy + 16, fill=(130, 150, 170), outline=INK, w=1)


def smoke(d, x, y, t, n=4):
    for i in range(n):
        ph = (t * 0.4 + i / n) % 1
        C(d, x + 10 * math.sin(i + t), y - ph * 90, 8 + ph * 18, fill=(130 + int(60 * ph),) * 3, outline=None)


def ground(d, y=GY):
    L(d, [(10, y), (410, y)], 3, INK)


def label_box(d, x, y, text, col, size=15, w=110):
    R(d, x - w / 2, y - 14, x + w / 2, y + 14, fill=col, outline=INK, w=2, rad=7)
    T(d, (x, y), text, size, (255, 255, 255) if sum(col) < 450 else INK)


def arrow(d, a, b, col=INK, w=3):
    L(d, [a, b], w, col)
    ang = math.atan2(b[1] - a[1], b[0] - a[0]); h = 11
    P(d, [b, (b[0] - h * math.cos(ang - .5), b[1] - h * math.sin(ang - .5)), (b[0] - h * math.cos(ang + .5), b[1] - h * math.sin(ang + .5))], fill=col)


def timeline(d, items, lt, dur, y0=180, gap=64):
    """items: [[date,text],...] revealed progressively across the scene."""
    n = len(items)
    for i, (dt, tx) in enumerate(items):
        at = 0.8 + (dur - 2.5) * (i / max(1, n))
        if lt < at:
            continue
        k = min(1.0, (lt - at) / 0.4)
        y = y0 + i * gap
        xo = (1 - k) * 60
        C(d, 36 + xo, y, 9, fill=GREEN, outline=INK, w=2)
        if i < n - 1:
            L(d, [(36 + xo, y + 9), (36 + xo, y + gap - 9)], 2, (150, 150, 150))
        T(d, (400 + xo, y - 12), dt, 17, GREEN, "rm")
        for j, ln in enumerate(split2(tx)):
            T(d, (400 + xo, y + 8 + j * 19), ln, 14, INK, "rm")


def split2(s, n=26):
    if len(s) <= n:
        return [s]
    words, a, b = s.split(), "", ""
    for w in words:
        if len((a + " " + w).strip()) <= n and not b:
            a = (a + " " + w).strip()
        else:
            b = (b + " " + w).strip()
    return [a, b]


# ------------------------------------------------------------------ stages
def tank(d, x, gy, w, t, flash=0.0, recoil=0.0):          # noqa: F811  (cannon points left, with muzzle flash + recoil)
    c = (86, 98, 74)
    x += recoil * 5
    R(d, x - w / 2, gy - w * 0.14, x + w / 2, gy, fill=(52, 52, 52), rad=w * 0.07)
    for i in range(6):
        C(d, x - w * 0.42 + i * w * 0.168, gy - w * 0.07, w * 0.048, fill=(150, 150, 150), outline=(90, 90, 90), w=1)
    R(d, x - w * 0.4, gy - w * 0.3, x + w * 0.4, gy - w * 0.13, fill=c, outline=INK, w=2, rad=4)
    R(d, x - w * 0.18, gy - w * 0.44, x + w * 0.18, gy - w * 0.28, fill=c, outline=INK, w=2, rad=4)
    bore = (x - w * 0.18 - w * 0.46 + recoil * 8, gy - w * 0.365 - 1.5 * math.sin(t * 5))
    L(d, [(x - w * 0.18, gy - w * 0.365), bore], 5.5, INK)
    if flash > 0.02:
        r_ = w * (0.07 + 0.16 * flash)
        for rr, col in ((r_ * 1.7, (255, 190, 70)), (r_ * 1.05, (255, 236, 150)), (r_ * 0.5, (255, 255, 255))):
            pts = []
            for i in range(18):
                a = math.pi + (i / 18 - 0.5) * math.tau * 0.85
                rad = rr * (1.0 if i % 2 == 0 else 0.4) * (1.6 if i in (8, 9) else 1.0)
                pts.append(((bore[0] + rad * math.cos(a)) * S, (bore[1] + rad * math.sin(a)) * S))
            d.polygon(pts, fill=col)


def chant_bubble(d, sc, lt, x=210, y=185):
    c = fx.chant_now(sc, lt)
    if c and c[0]:
        fx.bubble(d, x, y, c[0], c[1])


def st_intro(d, t, lt, dur, sc):
    skyline(d)
    ground(d)
    person(d, 210, GY, 215, t, "wave", INK, band=GREEN)
    T(d, (210, 180), "الثورة السورية", 36, RED)
    T(d, (210, 222), "من البداية إلى اليوم", 20, GREY)

def st_protest(d, t, lt, dur, sc):
    skyline(d, GY - 6)
    ground(d)
    back = [(16, "fist", None), (138, "sign", "سلمية"), (272, "fist", None), (398, "sign", "معًا")]
    for i, (x, pose, sg) in enumerate(back):
        person(d, x + 3 * math.sin(t * 1.2 + i), GY - 34, 140, t, pose, (74, 78, 86), sign=sg, ph=i * 0.37, band=GREEN)
    front = [(72, "sign", "حرية"), (205, "flag", None), (340, "sign", "كرامة")]
    for i, (x, pose, sg) in enumerate(front):
        if pose == "flag":
            person(d, x, GY, 205, t, "fist", INK, ph=i * 0.5, band=GREEN, prop="flag")
        else:
            person(d, x, GY, 205, t, pose, INK, sign=sg, ph=i * 0.5 + 0.2, band=GREEN)
    chant_bubble(d, sc, lt, 210, 165)

def st_crackdown(d, t, lt, dur, sc):
    ground(d)
    f = lt / dur
    flee = dur * 0.36
    kt = min(1.0, lt / (dur * 0.14)); kt = 1 - (1 - kt) ** 2
    fl, rc = fx.shots(sc, "tank", lt)
    tank(d, 600 - 250 * kt, GY - 6, 190, t, fl, rc)                              # tank behind the line
    for who, x0, sg in (("p1", 80, "حرية"), ("p3", 255, "سلمية")):                 # unarmed protesters
        pr = fx.falling(sc, who, lt)
        if pr is not None:
            person(d, x0, GY, 150, t, "fall", INK, prog=pr, band=GREEN)
        elif lt > flee + (0.0 if who == "p1" else 1.0):
            x = x0 - (lt - flee) * 95
            if x > -40:
                person(d, x, GY, 150, t, "run", INK, flip=-1, ph=0.3, band=GREEN)
        else:
            person(d, x0, GY, 150, t, "sign", INK, sign=sg, ph=0.4, band=GREEN)
    soldier(d, 292, GY, 170, t, sc, lt, "s1", ph=0.3)
    if f < 0.5:
        soldier(d, 378, GY, 170, t, sc, lt, "s2", ph=0.7)
    elif f < 0.58:
        person(d, 378, GY, 170, t, "hands_up", GREEN, flip=-1, band=GREEN)
    else:                                                                         # the defector walks over to the people
        x = max(200, 378 - (f - 0.58) * dur * 40)
        person(d, x, GY, 170, t, "walk" if x > 200 else "fist", GREEN, flip=-1, band=GREEN)
        if x <= 200:
            T(d, (200, 300), "انشقاق", 22, GREEN)

def st_world(d, t, lt, dur, sc):
    ground(d)
    person(d, 80, GY, 175, t, "stand", RED, helmet=True); label_box(d, 80, 322, "النظام", RED, 14, 80)
    person(d, 210, GY, 175, t, "stand", GREEN, band=GREEN); label_box(d, 210, 322, "المعارضة", GREEN, 14, 80)
    person(d, 340, GY, 175, t, "stand", YELLOW, band=YELLOW); label_box(d, 340, 322, "الأكراد", YELLOW, 14, 80)
    for i, (lab, tx, col) in enumerate([("إيران", 60, RED), ("حزب الله", 120, RED), ("تركيا", 200, GREEN), ("دول عربية وغربية", 270, GREEN)]):
        if lt > 1 + i * 0.8:
            label_box(d, tx + (20 if i == 3 else 0), 190, lab, (240, 240, 235), 13, 110 if i == 3 else 78)
            arrow(d, (tx + (20 if i == 3 else 0), 206), (80 if col == RED else 210, 304), col, 2.5)

def st_chemical(d, t, lt, dur, sc):
    ground(d)
    for i, x in enumerate([80, 190, 300]):
        building(d, x, GY, 80, 120 + 30 * (i % 2), 0, False)
    k = min(1.0, lt / 5.0)
    cloud(d, 190, 365 - 20 * k, 38 + 42 * k, t)
    cloud(d, 90, 350, 25 + 30 * k, t + 1)
    person(d, 372, GY, 150, t, "cower", INK, ph=0.2)
    person(d, 36, GY, 175, t, "sad", INK, ph=0.6, flip=1)
    T(d, (210, 165), "غاز السارين", 26, (100, 120, 50))
    T(d, (210, 200), "الغوطة الشرقية", 18, GREY)

def st_isis(d, t, lt, dur, sc):
    ground(d)
    for i, (x, who) in enumerate([(78, "y1"), (150, "y2")]):
        fl, rc = fx.shots(sc, who, lt)
        person(d, x, GY, 175, t, "aim", YELLOW, ph=i * 0.4, flip=1, prop="rifle", flash=fl, recoil=rc, band=YELLOW)
    person(d, 24, GY, 120, t, "cower", YELLOW)
    for i in range(3):
        x = 470 - ((lt * 16) % 170) - i * 62
        fl, rc = fx.shots(sc, f"d{i}", lt)
        person(d, x, GY, 165, t, "walk", (38, 38, 42), ph=i * 0.4, flip=-1, prop="rifle", flash=fl)
    for i in range(2):
        jet(d, 80 + ((lt * 60 + i * 200) % 440) - 20, 235 + i * 40, 70)
    T(d, (210, 190), "كوباني", 26, INK)

def st_jets_boats(d, t, lt, dur, sc):
    n = 0
    for e in fx.events(sc, "jet"):
        a = (lt - e["t"]) / e.get("dur", 5.0)
        if 0 <= a <= 1:
            jet(d, -70 + a * 560, 215 + 38 * (n % 3), 90)
            L(d, [(-70 + a * 560 - 45, 215 + 38 * (n % 3) + 2), (-70 + a * 560 - 150, 215 + 38 * (n % 3) + 4)], 3, (205, 205, 205))
        n += 1
    waves(d, 480, 10, 410, t)
    waves(d, 500, 10, 410, t + 1, (90, 140, 190))
    boat(d, 90 + (lt * 22) % 260, 470, 140, t, 4)
    T(d, (210, 160), "قصف وحصار", 22, RED)

def boat(d, x, y, w, t, n=4):                                  # noqa: F811
    y += 4 * math.sin(t * 2 + x)
    for i in range(n):
        person(d, x - w * 0.32 + i * w * 0.21, y - 3, 60, t, "sit", INK, ph=i * 0.3, shadow=False)
    P(d, [(x - w / 2, y - 8), (x + w / 2, y - 8), (x + w * 0.38, y + 14), (x - w * 0.38, y + 14)], fill=(150, 100, 60), outline=INK)

def st_ruins(d, t, lt, dur, sc):
    ground(d)
    for i, x in enumerate([70, 170, 270, 365]):
        building(d, x, GY, 70, 110 + 40 * ((i * 3) % 3), 0, True, (190, 180, 160))
    smoke(d, 170, 400, t); smoke(d, 300, 390, t + .5)
    person(d, 215, GY, 165, t, "sad_walk", INK, ph=0)
    person(d, 28, GY, 105, t, "cower", INK, ph=0.5)

def st_quake(d, t, lt, dur, sc):
    ground(d)
    amp = 5 if (lt > dur * 0.5) else 0
    for i, x in enumerate([90, 200, 310]):
        building(d, x, GY, 80, 140 + 30 * (i % 2), amp * math.sin(t * 40 + i), lt > dur * 0.6)
    if lt <= dur * 0.5:
        person(d, 140, GY, 170, t, "stand", GREEN, band=GREEN); person(d, 280, GY, 170, t, "stand", BLUE, flip=-1)
        L(d, [(160, GY - 112), (260, GY - 112)], 3, INK)
        T(d, (210, 260), "وقف إطلاق النار", 22, GREEN)
    else:
        person(d, 40, GY, 130, t, "cower", INK, ph=0.1); person(d, 385, GY, 130, t, "cower", INK, ph=0.6, flip=-1)
        T(d, (210, 260), "زلزال 6 فبراير 2023", 22, RED)

def st_toll(d, t, lt, dur, sc):
    st = sc["stat"]
    k = min(1.0, lt / 4.0); k = 1 - (1 - k) ** 3
    val = int(st["value"] * k)
    T(d, (210, 250), f"{val:,}", 58, RED)
    T(d, (210, 305), st["label"], 18, INK)
    T(d, (210, 335), st["note"], 13, GREY)
    n = 30
    for i in range(n):
        if i / n < k:
            x = 30 + (i % 15) * 25; y = 460 + (i // 15) * 62
            person(d, x, y, 46, t, "stand", (110, 110, 120), ph=i * 0.21, shadow=False)

def st_march(d, t, lt, dur, sc):
    ground(d)
    for i in range(4):
        person(d, 62 + i * 62 - (lt * 8) % 20, GY, 150, t, "march", GREEN, ph=i * 0.25, band=GREEN, prop="flag" if i == 1 else None)
    timeline(d, sc["timeline"], lt, dur, y0=175, gap=62)

def st_celebrate(d, t, lt, dur, sc):
    skyline(d, GY - 6)
    ground(d)
    for i in range(5):
        person(d, 55 + i * 78, GY, 165, t, "jump", INK, ph=i * 0.43, band=[GREEN, RED, INK][i % 3], prop="flag" if i in (1, 3) else None)
    for i in range(24):
        x = (i * 83 + lt * 30) % 420; y = (i * 47 + lt * 70) % 420 + 120
        col = [RED, GREEN, YELLOW, BLUE][i % 4]
        R(d, x, y, x + 7, y + 7, fill=col)
    for e in fx.events(sc, "firework"):
        col = [(255, 90, 80), (110, 220, 130), (255, 215, 80), (120, 180, 255)][int(e["t"] * 7) % 4]
        if CANVAS is not None:
            fx.fx_firework(CANVAS, e["x"] * S, e["y"] * S, lt - e["t"], col)
    T(d, (210, 175), "احتفالات في الساحات", 24, GREEN)
    chant_bubble(d, sc, lt, 210, 230)

def st_transition(d, t, lt, dur, sc):
    ground(d)
    person(d, 120, GY, 130, t, "stand", GREEN, band=GREEN); person(d, 300, GY, 130, t, "stand", YELLOW, flip=-1, band=YELLOW)
    L(d, [(140, GY - 84), (280, GY - 84)], 3, INK)
    timeline(d, sc["timeline"], lt, dur, y0=165, gap=68)

def st_handshake(d, t, lt, dur, sc):
    ground(d)
    person(d, 115, GY, 190, t, "stand", GREEN, band=GREEN); person(d, 305, GY, 190, t, "stand", YELLOW, flip=-1, band=YELLOW)
    arrow(d, (150, GY - 120), (270, GY - 120), INK, 3); arrow(d, (270, GY - 104), (150, GY - 104), INK, 3)
    T(d, (210, 200), "اتفاق 30 يناير 2026", 24, GREEN)
    T(d, (210, 238), "دمج تدريجي في مؤسسات الدولة", 16, GREY)

def st_closing(d, t, lt, dur, sc):
    k = min(1.0, lt / 6.0)
    sy = GY - 10 - 150 * k
    C(d, 210, sy, 62, fill=(250, 200, 80), outline=None)
    for i in range(12):
        a = i * math.pi / 6 + t * 0.3
        L(d, [(210 + 74 * math.cos(a), sy + 74 * math.sin(a)), (210 + 96 * math.cos(a), sy + 96 * math.sin(a))], 3, (250, 200, 80))
    R(d, 0, GY, 420, 600, fill=PAPER)
    skyline(d, GY, seed=5)
    ground(d)
    person(d, 210, GY, 160, t, "stand", INK, band=GREEN, prop="flag")
    for i in range(5):                                         # birds
        bx = (60 + i * 70 + lt * 14) % 460 - 20; by = 215 + 22 * math.sin(i * 1.7) + 4 * math.sin(t * 6 + i)
        L(d, [(bx - 7, by + 3 * math.sin(t * 9 + i)), (bx, by), (bx + 7, by + 3 * math.sin(t * 9 + i))], 2, (70, 70, 80))
    if lt > dur * 0.55:
        for i, ln in enumerate(["المصادر: مفوضية الأمم المتحدة لحقوق الإنسان،", "خدمة أبحاث الكونغرس، مجلس الأمن،", "المجلس الأطلسي، معهد الشرق الأوسط"]):
            T(d, (210, 548 + i * 17), ln, 12, GREY)


STAGES = {
    "intro": st_intro, "protest": st_protest, "crackdown": st_crackdown, "world": st_world, "chemical": st_chemical,
    "isis": st_isis, "jets_boats": st_jets_boats, "ruins": st_ruins, "quake": st_quake, "toll": st_toll,
    "march": st_march, "celebrate": st_celebrate, "transition": st_transition, "handshake": st_handshake,
    "closing": st_closing,
}
