"""A proper stickman rig: forward-kinematics skeleton (thigh/shin, upper-arm/forearm), tapered limbs, expressive face,
hand-drawn feel via smooth easing, props (sign, Syrian independence flag, rifle) and procedural animation cycles.

Everything is drawn straight onto the supersampled PIL canvas (`d`), so it stays razor sharp at any scale.
Angles are measured from "straight down" and grow toward the direction the figure faces (flip=-1 mirrors it).
"""
import math
from textutil import S, font, draw_text

INK = (30, 30, 36)


def _mix(c, w, k):
    return tuple(int(c[i] * (1 - k) + w[i] * k) for i in range(3))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ----------------------------------------------------------------------------- primitives
def circle(d, x, y, r, fill=None, outline=None, w=0):
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill, outline=outline, width=max(0, int(w * S)))


def limb(d, a, b, w0, w1, col):
    """Tapered capsule from a (width w0) to b (width w1); coordinates/widths in design px."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / ln, dx / ln
    pts = [(a[0] + nx * w0 / 2, a[1] + ny * w0 / 2), (b[0] + nx * w1 / 2, b[1] + ny * w1 / 2),
           (b[0] - nx * w1 / 2, b[1] - ny * w1 / 2), (a[0] - nx * w0 / 2, a[1] - ny * w0 / 2)]
    d.polygon([(x * S, y * S) for x, y in pts], fill=col)
    circle(d, a[0], a[1], w0 / 2, fill=col)
    circle(d, b[0], b[1], w1 / 2, fill=col)


def star(d, cx, cy, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append(((cx + rr * math.cos(a)) * S, (cy + rr * math.sin(a)) * S))
    d.polygon(pts, fill=col)


def flag(d, bx, by, tx, ty, w, h, t, ph=0.0, flip=1):
    """Syrian independence flag on a pole from base (bx,by) to top (tx,ty); cloth waves in the wind."""
    limb(d, (bx, by), (tx, ty), 2.6, 2.6, (95, 70, 45))
    circle(d, tx, ty, 2.4, fill=(95, 70, 45))
    n = 14
    green, white, black, red = (0, 122, 61), (250, 250, 250), (20, 20, 20), (206, 17, 38)
    top = ty + 2
    for i in range(n):
        x0 = tx + flip * (w * i / n); x1 = tx + flip * (w * (i + 1) / n)
        amp = 2 + 5 * (i / n)
        y0 = top + amp * math.sin(t * 7 - i * 0.62 + ph); y1 = top + amp * math.sin(t * 7 - (i + 1) * 0.62 + ph)
        for k, c in enumerate((green, white, black)):
            ya0, ya1 = y0 + h * k / 3, y1 + h * k / 3
            yb0, yb1 = y0 + h * (k + 1) / 3 + 0.4, y1 + h * (k + 1) / 3 + 0.4
            d.polygon([(x0 * S, ya0 * S), (x1 * S, ya1 * S), (x1 * S, yb1 * S), (x0 * S, yb0 * S)], fill=c)
    for j in range(3):                          # three red stars on the white band
        f = (j + 1) / 4
        i = int(f * n)
        amp = 2 + 5 * (i / n)
        sy = top + amp * math.sin(t * 7 - i * 0.62 + ph) + h * 0.5
        star(d, tx + flip * w * f, sy, h * 0.13, red)


def rifle(d, hand_back, hand_front, col, flash=0.0, flip=1):
    """Assault-rifle silhouette pointing forward from the shooter's hands; returns the muzzle position."""
    ux, uy = flip * 0.998, -0.06
    butt = (hand_back[0] - ux * 17, hand_back[1] - uy * 17 + 2.5)
    muzzle = (hand_front[0] + ux * 24, hand_front[1] + uy * 24)
    limb(d, butt, (hand_back[0] - ux * 2, hand_back[1] - uy * 2), 6.5, 5.0, (92, 64, 40))          # wooden stock
    limb(d, (hand_back[0] - ux * 3, hand_back[1] - uy * 3), muzzle, 5.0, 3.2, (42, 42, 48))          # receiver + barrel
    limb(d, (hand_back[0] + ux * 5, hand_back[1] + uy * 5), (hand_back[0] + ux * 9, hand_back[1] + 12), 3.6, 3.2, (42, 42, 48))  # magazine
    limb(d, (hand_front[0] + ux * 3, hand_front[1] + uy * 3), (hand_front[0] + ux * 16, hand_front[1] + uy * 16 - 1), 5.6, 5.0, (92, 64, 40))
    if flash > 0.02:
        fx, fy = muzzle[0] + ux * 4, muzzle[1] + uy * 4
        r = 6 + 11 * flash
        for rr, c in ((r * 1.7, (255, 190, 70)), (r * 1.1, (255, 236, 150)), (r * 0.5, (255, 255, 255))):
            pts = []
            for i in range(16):
                a = (0 if flip > 0 else math.pi) + (i / 16 - 0.5) * math.tau * 0.9
                rad = rr * (1.0 if i % 2 == 0 else 0.4) * (1.5 if i in (7, 8) else 1.0)
                pts.append(((fx + rad * math.cos(a)) * S, (fy + rad * math.sin(a)) * S))
            d.polygon(pts, fill=c)
    return muzzle


# ----------------------------------------------------------------------------- poses
def _osc(u, f, a=1.0, p=0.0): return a * math.sin(u * f * math.tau + p)


def pose(name, u, prog=0.0, aim_recoil=0.0):
    """-> dict(lean, head, arms=[(upper,fore)x2 back,front], legs=[(thigh,shin)x2 back,front], lift, mouth, brow, x_shift, rot)"""
    P = dict(lean=2.0, head=0.0, arms=[(8, 12), (-6, 8)], legs=[(7, 3), (-5, -2)], lift=0.0, mouth="line", brow="flat",
             x=0.0, rot=0.0, eyes=1.0)
    if name in ("stand", "idle"):
        b = _osc(u, 0.4, 1.2)
        P.update(lean=1.5 + b * 0.3, head=_osc(u, 0.25, 3), arms=[(9 + b, 14 + b), (-7 - b, 6 - b)], legs=[(6, 2), (-5, -3)],
                 mouth="smile" if int(u * 0.2) % 3 == 0 else "line")
    elif name in ("walk", "sad_walk"):
        sad = name == "sad_walk"
        f = 0.75 if sad else 1.0
        p = u * f * math.tau
        amp = 20 if sad else 26
        legs = []
        for k in (0, math.pi):
            th = amp * math.sin(p + k) + 3
            flex = (8 if sad else 6) + (46 if not sad else 30) * max(0.0, math.cos(p + k)) ** 1.3
            legs.append((th, th - flex))
        arm_amp = 8 if sad else 24
        arms = []
        for k in (math.pi, 0):
            up = arm_amp * math.sin(p + k) + (6 if sad else 0)
            arms.append((up, up + (8 if sad else 22 + 8 * max(0, math.sin(p + k)))))
        P.update(lean=16 if sad else 5, head=26 if sad else 0, arms=arms, legs=legs, mouth="frown" if sad else "line",
                 brow="sad" if sad else "flat")
    elif name == "run":
        p = u * 2.1 * math.tau
        legs = []
        for k in (0, math.pi):
            th = 52 * math.sin(p + k) + 8
            flex = 14 + 100 * max(0.0, math.cos(p + k)) ** 1.5
            legs.append((th, th - flex))
        arms = []
        for k in (math.pi, 0):
            up = 48 * math.sin(p + k)
            arms.append((up, up + 85))
        P.update(lean=18, head=-6, arms=arms, legs=legs, lift=0.05 * max(0.0, math.sin(2 * p + 1.2)), mouth="open", brow="fear")
    elif name in ("fist", "chant"):
        bn = abs(math.sin(u * 2 * math.tau * 0.5))
        up = 168 + 7 * math.sin(u * 5)
        P.update(lean=-2, head=-9, arms=[(14, 38), (up, up + 4 * math.sin(u * 5))], legs=[(10 + 4 * bn, 4), (-8, -3)],
                 lift=0.012 * bn, mouth="open" if math.sin(u * 9) > -0.2 else "line", brow="angry")
    elif name == "hands_up":
        tr = 1.6 * math.sin(u * 19)
        P.update(lean=-3, head=-4, arms=[(152 + tr, 176 + tr), (-1 * 0 + 150 - tr, 176 - tr)], legs=[(8, 4), (-6, -2)],
                 mouth="open", brow="fear")
    elif name == "sign":
        bn = abs(math.sin(u * 1.5 * math.tau * 0.5))
        P.update(lean=0, head=-3, arms=[(150, 178), (146, 176)], legs=[(7 + 3 * bn, 3), (-6, -2)], lift=0.008 * bn,
                 mouth="open" if math.sin(u * 6.5) > 0 else "line", brow="angry")
    elif name in ("jump", "cheer"):
        j = abs(math.sin(u * 1.5 * math.pi))
        a = 158 + 18 * j
        P.update(lean=-3, head=-8, arms=[(a, a + 6), (a + 8, a + 14)], legs=[(18 * j + 4, 4 - 55 * j), (-14 * j, -8 - 40 * j)],
                 lift=0.22 * j, mouth="smile_open", brow="happy")
    elif name == "wave":
        P.update(lean=0, head=-4, arms=[(8, 13), (148, 152 + 30 * math.sin(u * 8))], mouth="smile", brow="happy")
    elif name == "point":
        P.update(lean=3, head=-2, arms=[(8, 13), (104, 108)], legs=[(10, 4), (-8, -3)], mouth="open", brow="angry")
    elif name == "sad":
        P.update(lean=14 + _osc(u, 0.3, 1.5), head=28, arms=[(5, 9), (-2, 6)], legs=[(10, 6), (-4, -6)], mouth="frown", brow="sad")
    elif name == "sit":
        P.update(lean=6, head=8, arms=[(40, 100), (30, 96)], legs=[(92, 4), (88, -2)], mouth="frown", brow="sad")
    elif name == "cower":
        tr = 1.8 * math.sin(u * 17)
        P.update(lean=38, head=24, arms=[(118 + tr, 232), (126 - tr, 236)], legs=[(104, 6), (96, -2)], mouth="open", brow="fear")
    elif name == "aim":
        P.update(lean=7 + aim_recoil * 2, head=-3, x=-aim_recoil * 2.2, arms=[(52, 96 - aim_recoil * 4), (80 + aim_recoil * 3, 92)],
                 legs=[(-16, -20), (22, 14)], mouth="line", brow="angry")
    elif name == "fall":
        k = ease(prog)
        P.update(lean=2, head=-20 * k, arms=[(60 * k + 8, 100 * k + 12), (120 * k - 6, 140 * k + 8)],
                 legs=[(6 + 30 * k, 3), (-5 - 12 * k, -2)], rot=-88 * k, mouth="open", brow="fear")
    elif name == "march":
        p = u * 1.15 * math.tau
        legs = []
        for k in (0, math.pi):
            th = 30 * math.sin(p + k) + 4
            legs.append((th, th - 6 - 50 * max(0.0, math.cos(p + k)) ** 1.3))
        arms = []
        for k in (math.pi, 0):
            up = 28 * math.sin(p + k)
            arms.append((up, up + 30))
        P.update(lean=7, head=-2, arms=arms, legs=legs, mouth="open", brow="angry")
    return P


# ----------------------------------------------------------------------------- the figure
def _fk(origin, ang, ln, fl):
    return (origin[0] + math.sin(math.radians(ang)) * ln * fl, origin[1] + math.cos(math.radians(ang)) * ln)


def figure(d, x, gy, h, t, name="stand", color=INK, head_fill=(247, 241, 227), flip=1, ph=0.0, speed=1.0,
           sign=None, prop=None, band=None, helmet=False, prog=0.0, flash=0.0, recoil=0.0, mouth=None, scarf=False,
           shadow=True, shadow_col=(222, 214, 196)):
    fl = 1 if flip >= 0 else -1
    u = t * speed + ph
    P = pose(name, u, prog, recoil)
    if mouth: P["mouth"] = mouth
    thigh, shin, torso, neck = h * 0.225, h * 0.225, h * 0.32, h * 0.035
    r = h * 0.10
    ua, fa = h * 0.165, h * 0.155
    wk = max(2.2, h * 0.052)

    # skeleton relative to hip at origin (0,0); ground solved afterwards
    hip = (0.0, 0.0)
    legs = []
    for (th, sh) in P["legs"]:
        knee = _fk(hip, th, thigh, fl)
        ank = _fk(knee, sh, shin, fl)
        legs.append((knee, ank))
    lean = math.radians(P["lean"])
    up = (math.sin(lean) * fl, -math.cos(lean))
    chest = (hip[0] + up[0] * torso * 0.93, hip[1] + up[1] * torso * 0.93)
    neck_p = (hip[0] + up[0] * torso, hip[1] + up[1] * torso)
    hd = math.radians(P["lean"] + P["head"])
    hv = (math.sin(hd) * fl, -math.cos(hd))
    head = (neck_p[0] + hv[0] * (neck + r * 0.9), neck_p[1] + hv[1] * (neck + r * 0.9))
    arms = []
    for (ua_a, fa_a) in P["arms"]:
        el = _fk(chest, ua_a, ua, fl)
        ha = _fk(el, fa_a, fa, fl)
        arms.append((el, ha))

    pts = [hip, chest, neck_p, head] + [p for a in arms for p in a] + [p for l in legs for p in l]
    rot = math.radians(P["rot"]) * fl
    low = max(max(l[1][1] for l in legs), hip[1])
    if abs(P["rot"]) > 1:                                  # rotate the whole body about the lowest foot (falls)
        foot = max((l[1] for l in legs), key=lambda p: p[1])
        c, s_ = math.cos(rot), math.sin(rot)

        def R_(p):
            dx, dy = p[0] - foot[0], p[1] - foot[1]
            return (foot[0] + dx * c - dy * s_, foot[1] + dx * s_ + dy * c)
        hip, chest, neck_p, head = map(R_, (hip, chest, neck_p, head))
        arms = [(R_(a), R_(b)) for a, b in arms]
        legs = [(R_(a), R_(b)) for a, b in legs]
        low = max(l[1][1] for l in legs); low = max(low, max(p[1] for p in (head, hip)) + 0)
    # ground contact
    lowest = max(max(l[1][1] for l in legs), hip[1] + 0, head[1] + (r if abs(P["rot"]) > 1 else 0))
    oy = gy - h * P["lift"] - lowest
    ox = x + P["x"] * h * 0.01 * fl

    def T_(p): return (ox + p[0], oy + p[1])
    hip, chest, neck_p, head = map(T_, (hip, chest, neck_p, head))
    arms = [(T_(a), T_(b)) for a, b in arms]
    legs = [(T_(a), T_(b)) for a, b in legs]

    back = _mix(color, (255, 255, 255), 0.28)
    # shadow
    if shadow:
        sh_k = 1.0 - min(0.5, P["lift"] * 1.6)
        d.ellipse([(x - h * 0.30 * sh_k) * S, (gy - h * 0.022) * S, (x + h * 0.30 * sh_k) * S, (gy + h * 0.022) * S], fill=shadow_col)

    def draw_leg(i, col):
        knee, ank = legs[i]
        limb(d, hip, knee, wk * 1.05, wk * 0.9, col)
        limb(d, knee, ank, wk * 0.9, wk * 0.72, col)
        toe = (ank[0] + fl * h * 0.07, ank[1] + h * 0.004)
        limb(d, ank, toe, wk * 0.72, wk * 0.6, col)

    def draw_arm(i, col, hand_col=None):
        el, ha = arms[i]
        limb(d, chest, el, wk * 0.85, wk * 0.74, col)
        limb(d, el, ha, wk * 0.74, wk * 0.62, col)
        circle(d, ha[0], ha[1], wk * 0.5, fill=hand_col or col)

    # draw order: back leg, back arm, torso, front leg, head, front arm
    draw_leg(0, back)
    draw_arm(0, back)
    limb(d, hip, neck_p, wk * 1.15, wk * 0.95, color)
    draw_leg(1, color)
    if scarf:
        for k in range(3):
            a0 = (neck_p[0], neck_p[1] + 1)
            a1 = (neck_p[0] - fl * (8 + 6 * k), neck_p[1] + 3 + 5 * math.sin(u * 8 + k))
            limb(d, a0, a1, 3.2 - k * 0.6, 1.6, band or (192, 57, 43))
    # --- head
    hc = head
    circle(d, hc[0], hc[1], r, fill=head_fill, outline=color, w=max(1.8, wk * 0.62))
    if helmet:
        hb = math.radians(P["lean"] + P["head"])
        pts_h = []
        for i in range(21):
            a = math.pi + i * math.pi / 20
            pts_h.append(((hc[0] + (r * 1.08) * math.cos(a)) * S, (hc[1] - r * 0.12 + (r * 1.08) * math.sin(a)) * S))
        d.polygon(pts_h, fill=(70, 78, 62))
        d.rectangle([(hc[0] - r * 1.1) * S, (hc[1] - r * 0.2) * S, (hc[0] + r * 1.1) * S, (hc[1] - r * 0.05) * S], fill=(70, 78, 62))
    if band and not helmet:
        d.rectangle([(hc[0] - r * 0.98) * S, (hc[1] - r * 0.55) * S, (hc[0] + r * 0.98) * S, (hc[1] - r * 0.28) * S], fill=band)
        for k in range(2):
            tail = (hc[0] - fl * (r * 1.0 + 9 + 4 * k), hc[1] - r * 0.4 + 4 * math.sin(u * 9 + k * 1.7) + k * 3)
            limb(d, (hc[0] - fl * r * 0.9, hc[1] - r * 0.42), tail, 2.6, 1.4, band)
    # face
    ex = fl * r * 0.34
    eyes = [(hc[0] + ex - r * 0.28, hc[1] - r * 0.12), (hc[0] + ex + r * 0.42, hc[1] - r * 0.12)]
    er = max(0.9, r * 0.12) * (1.25 if P["brow"] == "fear" else 1.0)
    for e in eyes:
        circle(d, e[0], e[1], er, fill=color)
    bw = max(1.2, r * 0.13)
    bk = P["brow"]
    for j, e in enumerate(eyes):
        side = -1 if j == 0 else 1
        by = e[1] - r * 0.27
        if bk == "angry":
            a, b = (e[0] - r * 0.22, by - r * 0.1 * -side * -1), (e[0] + r * 0.22, by + r * 0.0)
            a = (e[0] - r * 0.22, by + (r * 0.12 if side == -1 else -r * 0.04)); b = (e[0] + r * 0.22, by + (-r * 0.04 if side == -1 else r * 0.12))
        elif bk == "sad":
            a = (e[0] - r * 0.22, by + (-r * 0.04 if side == -1 else r * 0.1)); b = (e[0] + r * 0.22, by + (r * 0.1 if side == -1 else -r * 0.04))
        elif bk == "fear":
            a = (e[0] - r * 0.22, by - r * 0.08); b = (e[0] + r * 0.22, by - r * 0.12 - (r * 0.06 if side == 1 else 0))
        elif bk == "happy":
            a = (e[0] - r * 0.2, by - r * 0.04); b = (e[0] + r * 0.2, by - r * 0.1)
        else:
            continue
        d.line([(a[0] * S, a[1] * S), (b[0] * S, b[1] * S)], fill=color, width=max(1, int(bw * S)))
    mx, my = hc[0] + ex + r * 0.07, hc[1] + r * 0.42
    mk = P["mouth"]
    if mk == "open":
        d.ellipse([(mx - r * 0.24) * S, (my - r * 0.14) * S, (mx + r * 0.24) * S, (my + r * 0.26) * S], fill=(60, 25, 28))
    elif mk == "smile_open":
        d.pieslice([(mx - r * 0.36) * S, (my - r * 0.3) * S, (mx + r * 0.36) * S, (my + r * 0.3) * S], 0, 180, fill=(60, 25, 28))
    elif mk == "smile":
        d.arc([(mx - r * 0.32) * S, (my - r * 0.3) * S, (mx + r * 0.32) * S, (my + r * 0.18) * S], 20, 160, fill=color, width=max(1, int(bw * S)))
    elif mk == "frown":
        d.arc([(mx - r * 0.3) * S, (my + r * 0.04) * S, (mx + r * 0.3) * S, (my + r * 0.46) * S], 200, 340, fill=color, width=max(1, int(bw * S)))
    else:
        d.line([((mx - r * 0.2) * S, (my + r * 0.05) * S), ((mx + r * 0.2) * S, (my + r * 0.05) * S)], fill=color, width=max(1, int(bw * S)))

    # --- props + front arm
    ha_front = arms[1][1]
    if prop == "rifle" or name == "aim":
        rifle(d, arms[0][1], ha_front, color, flash, fl)
    draw_arm(1, color, _mix(color, (255, 255, 255), 0.05))
    if sign:
        hx = (arms[0][1][0] + arms[1][1][0]) / 2
        hy = min(arms[0][1][1], arms[1][1][1])
        bw_, bh_ = h * 0.66, h * 0.31
        limb(d, (hx, hy + h * 0.06), (hx, hy - bh_ - 4), 2.4, 2.4, (95, 70, 45))
        d.rounded_rectangle([(hx - bw_ / 2) * S, (hy - bh_ - 4) * S, (hx + bw_ / 2) * S, (hy - 4) * S], radius=3 * S, fill=(255, 255, 255),
                            outline=color, width=int(2.2 * S))
        draw_text(d, (hx * S, (hy - bh_ / 2 - 4) * S), sign, font(max(11, h * 0.16)), color, "mm")
    if prop == "flag":
        flag(d, ha_front[0], ha_front[1] + h * 0.16, ha_front[0], ha_front[1] - h * 0.62, h * 0.66, h * 0.36, t, ph, fl)
    return dict(head=head, hand=ha_front, hip=hip, muzzle=None)
