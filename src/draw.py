"""Stickman primitives + animated 'stage' scenes (left panel, 420x600 design px)."""
import math
from textutil import S, font, draw_text, text_w
import actors as A

INK = (30, 30, 36)
RED = (192, 57, 43)
GREEN = (46, 139, 87)
YELLOW = (224, 176, 0)
GREY = (90, 90, 98)
PAPER = (247, 241, 227)
GY = 520  # ground line


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


def person(d, x, gy, h, t, pose="stand", color=INK, sign=None, ph=0.0, flip=1, head_fill=PAPER):
    lw = max(2.6, h * 0.05)
    r = h * 0.11
    w = math.sin(t * 6 + ph)
    legs = (8, -8); arms = (18, -18)
    bob = 0.0
    if pose == "walk":
        legs = (30 * w, -30 * w); arms = (-25 * w, 25 * w); bob = abs(w) * h * 0.02
    elif pose == "run":
        w = math.sin(t * 11 + ph)
        legs = (45 * w, -45 * w); arms = (-55 * w, 55 * w); bob = abs(w) * h * 0.05
    elif pose == "fist":
        arms = (18, 160 + 10 * math.sin(t * 5 + ph))
    elif pose == "hands_up":
        arms = (-(155 + 10 * math.sin(t * 6 + ph)), 155 + 10 * math.sin(t * 6 + ph + 1))
    elif pose == "sign":
        arms = (-172, 172); bob = abs(math.sin(t * 3 + ph)) * h * 0.015
    elif pose == "jump":
        j = abs(math.sin(t * 4 + ph))
        bob = j * h * 0.25
        arms = (-(150 + 20 * j), 150 + 20 * j); legs = (15, -15)
    elif pose == "wave":
        arms = (18, 140 + 25 * math.sin(t * 7))
    elif pose == "sad":
        arms = (10, -10)
    elif pose == "point":
        arms = (18, -85)
    if A.available():
        clip = A.POSE_TO_CLIP.get(pose, "idle")
        A.paste(d._image, clip, t, x * S, gy * S, h * S * 0.88, color, head_fill, flip=flip, phase=ph * 0.37)
        top_head = gy - h * 1.02
        sh = (x, top_head + h * 0.2)
    else:
        gy = gy - bob
        hip = (x, gy - h * 0.42)
        neck = (x, hip[1] - h * 0.30)
        head = (x + (h * 0.02 * flip if pose == "sad" else 0), neck[1] - r * 0.95)
        sh = (x, neck[1] + h * 0.04)

        def end(p, a, ln):
            rad = math.radians(a)
            return (p[0] + ln * math.sin(rad) * flip, p[1] + ln * math.cos(rad))
        for a in legs:
            L(d, [hip, end(hip, a, h * 0.43)], lw, color)
        for a in arms:
            L(d, [sh, end(sh, a, h * 0.30)], lw, color)
        L(d, [neck, hip], lw, color)
        C(d, head[0], head[1], r, fill=head_fill, outline=color, w=lw)
        if pose == "sad":
            L(d, [(head[0] - r * .4, head[1] + r * .35), (head[0] + r * .4, head[1] + r * .35)], 1.5, color)
    if sign:
        top = (gy - h * 1.05) if A.available() else sh[1] - h * 0.30
        bw, bh = h * 0.64, h * 0.30
        R(d, x - bw / 2, top - bh, x + bw / 2, top, fill=(255, 255, 255), outline=color, w=2.2, rad=3)
        T(d, (x, top - bh / 2), sign, max(11, h * 0.16), color)


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
def st_intro(d, t, lt, dur, sc):
    ground(d)
    person(d, 210, GY, 170, t, "wave", INK)
    T(d, (210, 300), "الثورة السورية", 34, RED)
    T(d, (210, 340), "من البداية إلى اليوم", 20, GREY)

def st_protest(d, t, lt, dur, sc):
    ground(d)
    signs = ["حرية", "كرامة", "سلمية", "معًا"]
    for i, s in enumerate(signs):
        x = 62 + i * 98 + 5 * math.sin(t + i)
        person(d, x, GY, 150, t, "sign", INK, sign=s, ph=i)

def st_crackdown(d, t, lt, dur, sc):
    ground(d)
    k = min(1.0, lt / 4.0)
    tank(d, 470 - 150 * k, GY, 170, t)
    for i in range(3):
        person(d, 45 + i * 45, GY, 120, t, "run" if lt < 7 else "sad", INK, ph=i)
    if lt > dur * 0.45:
        person(d, 205, GY, 120, t, "hands_up", GREEN)
        T(d, (205, 330), "انشقاق", 18, GREEN)

def st_world(d, t, lt, dur, sc):
    ground(d)
    person(d, 80, GY, 125, t, "stand", RED); label_box(d, 80, 375, "النظام", RED, 14, 80)
    person(d, 210, GY, 125, t, "stand", GREEN); label_box(d, 210, 375, "المعارضة", GREEN, 14, 80)
    person(d, 340, GY, 125, t, "stand", YELLOW); label_box(d, 340, 375, "الأكراد", YELLOW, 14, 80)
    for i, (lab, tx, col) in enumerate([("إيران", 60, RED), ("حزب الله", 120, RED), ("تركيا", 200, GREEN), ("دول عربية وغربية", 270, GREEN)]):
        if lt > 1 + i * 0.8:
            label_box(d, tx + (20 if i == 3 else 0), 220, lab, (240, 240, 235), 13, 110 if i == 3 else 78)
            arrow(d, (tx + (20 if i == 3 else 0), 236), (80 if col == RED else 210, 358), col, 2.5)

def st_chemical(d, t, lt, dur, sc):
    ground(d)
    for i, x in enumerate([80, 190, 300]):
        building(d, x, GY, 80, 120 + 30 * (i % 2), 0, False)
    k = min(1.0, lt / 5.0)
    cloud(d, 190, 365 - 20 * k, 38 + 42 * k, t)
    cloud(d, 90, 350, 25 + 30 * k, t + 1)
    person(d, 370, GY, 90, t, "stand", INK)
    C(d, 370, GY - 90 * 0.95 - 4, 9, fill=(120, 120, 120))  # mask hint
    T(d, (210, 165), "غاز السارين", 26, (100, 120, 50))
    T(d, (210, 200), "الغوطة الشرقية", 18, GREY)

def st_isis(d, t, lt, dur, sc):
    ground(d)
    # besieged circle (Kobani)
    for i in range(4):
        a = i * math.pi / 2 + 0.4
        person(d, 100 + 40 * math.cos(a), GY, 95, t, "stand", YELLOW)
    for i in range(3):
        person(d, 400 - ((lt * 18) % 130) - i * 34, GY, 100, t, "walk", (50, 50, 55), ph=i)
    for i in range(2):
        jet(d, 80 + ((lt * 60 + i * 200) % 440) - 20, 250 + i * 40, 70)
    T(d, (210, 190), "كوباني", 26, INK)

def st_jets_boats(d, t, lt, dur, sc):
    for i in range(3):
        jet(d, ((lt * 70 + i * 150) % 520) - 50, 220 + i * 45, 80)
    waves(d, 480, 10, 410, t)
    waves(d, 500, 10, 410, t + 1, (90, 140, 190))
    boat(d, 90 + (lt * 22) % 260, 470, 120, t, 4)
    T(d, (210, 160), "قصف وحصار", 22, RED)

def st_ruins(d, t, lt, dur, sc):
    ground(d)
    for i, x in enumerate([70, 170, 270, 365]):
        building(d, x, GY, 70, 110 + 40 * ((i * 3) % 3), 0, True, (190, 180, 160))
    smoke(d, 170, 400, t); smoke(d, 300, 390, t + .5)
    person(d, 215, GY, 90, t, "walk", INK, ph=0)

def st_quake(d, t, lt, dur, sc):
    ground(d)
    amp = 5 if (lt > dur * 0.5) else 0
    for i, x in enumerate([90, 200, 310]):
        building(d, x, GY, 80, 140 + 30 * (i % 2), amp * math.sin(t * 40 + i), lt > dur * 0.6)
    # ceasefire handshake (two persons) early
    if lt <= dur * 0.5:
        person(d, 150, GY, 110, t, "stand", GREEN); person(d, 270, GY, 110, t, "stand", (59, 126, 161), flip=-1)
        L(d, [(165, GY - 80), (255, GY - 80)], 3, INK)
        T(d, (210, 260), "وقف إطلاق النار", 22, GREEN)
    else:
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
            x = 30 + (i % 15) * 25; y = 430 + (i // 15) * 55
            person(d, x, y, 38, t, "stand", (110, 110, 120))

def st_march(d, t, lt, dur, sc):
    ground(d)
    for i in range(4):
        person(d, 60 + i * 55 - (lt * 8) % 20, GY, 90, t, "walk", GREEN, ph=i)
    timeline(d, sc["timeline"], lt, dur, y0=175, gap=62)

def st_celebrate(d, t, lt, dur, sc):
    ground(d)
    for i in range(5):
        person(d, 55 + i * 78, GY, 100, t, "jump", INK, ph=i * 1.3)
    for i in range(24):
        x = (i * 83 + lt * 30) % 420; y = (i * 47 + lt * 70) % 420 + 120
        col = [RED, GREEN, YELLOW, (59, 126, 161)][i % 4]
        R(d, x, y, x + 7, y + 7, fill=col)
    T(d, (210, 175), "احتفالات في الساحات", 24, GREEN)

def st_transition(d, t, lt, dur, sc):
    ground(d)
    person(d, 130, GY, 75, t, "stand", GREEN); person(d, 290, GY, 75, t, "stand", YELLOW, flip=-1)
    L(d, [(142, GY - 48), (278, GY - 48)], 3, INK)
    timeline(d, sc["timeline"], lt, dur, y0=165, gap=68)

def st_handshake(d, t, lt, dur, sc):
    ground(d)
    person(d, 120, GY, 120, t, "stand", GREEN); person(d, 300, GY, 120, t, "stand", YELLOW, flip=-1)
    arrow(d, (150, GY - 80), (270, GY - 80), INK, 3); arrow(d, (270, GY - 70), (150, GY - 70), INK, 3)
    T(d, (210, 250), "اتفاق 30 يناير 2026", 22, GREEN)
    T(d, (210, 285), "دمج تدريجي في مؤسسات الدولة", 16, GREY)

def st_closing(d, t, lt, dur, sc):
    # sunrise
    k = min(1.0, lt / 6.0)
    sy = GY - 10 - 150 * k
    C(d, 210, sy, 62, fill=(250, 200, 80), outline=None)
    for i in range(12):
        a = i * math.pi / 6 + t * 0.3
        L(d, [(210 + 74 * math.cos(a), sy + 74 * math.sin(a)), (210 + 96 * math.cos(a), sy + 96 * math.sin(a))], 3, (250, 200, 80))
    R(d, 0, GY, 420, 600, fill=PAPER)
    ground(d)
    person(d, 210, GY, 150, t, "stand", INK)
    if lt > dur * 0.55:
        for i, ln in enumerate(["المصادر: مفوضية الأمم المتحدة لحقوق الإنسان،", "خدمة أبحاث الكونغرس، مجلس الأمن،", "المجلس الأطلسي، معهد الشرق الأوسط"]):
            T(d, (210, 548 + i * 17), ln, 12, GREY)


STAGES = {
    "intro": st_intro, "protest": st_protest, "crackdown": st_crackdown, "world": st_world, "chemical": st_chemical,
    "isis": st_isis, "jets_boats": st_jets_boats, "ruins": st_ruins, "quake": st_quake, "toll": st_toll,
    "march": st_march, "celebrate": st_celebrate, "transition": st_transition, "handshake": st_handshake,
    "closing": st_closing,
}
