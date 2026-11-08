"""Pro YouTube thumbnail: composite several Wikimedia Commons photos + generated flag + type, 1920x1080.
python src/thumb_pro.py <photos_dir> <out_png>"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops
W, H = 1920, 1080
FONT = os.path.join(os.path.dirname(__file__), "..", "assets", "NotoSansArabic-Bold.ttf")
rng = np.random.default_rng(7)

def font(sz): return ImageFont.truetype(FONT, sz, layout_engine=ImageFont.Layout.RAQM)
def cover(im, w, h):
    s = max(w / im.width, h / im.height); im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2; return im.crop((x, y, x + w, y + h))
def arr(im): return np.asarray(im.convert("RGB")).astype("float32") / 255
def img(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
def screen(a, b): return 1 - (1 - a) * (1 - b)
def grad_mask(w, h, fn):
    yy, xx = np.mgrid[0:h, 0:w]; return np.clip(fn(xx / w, yy / h), 0, 1).astype("float32")
def tint(a, mul, lift=(0, 0, 0)): return a * np.array(mul) + np.array(lift)
def smooth(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def text_mask(txt, xy, sz, anchor="ra", stroke=0):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).text(xy, txt, font=font(sz), fill=255, anchor=anchor, direction="rtl", language="ar", stroke_width=stroke)
    return m

def layer_over(base, layer_rgb, mask):  # arrays
    return base * (1 - mask[..., None]) + layer_rgb * mask[..., None]

def flag(w=1000, h=660):
    f = Image.new("RGB", (w, h)); d = ImageDraw.Draw(f)
    d.rectangle((0, 0, w, h // 3), fill=(0, 128, 58)); d.rectangle((0, h // 3, w, 2 * h // 3), fill=(250, 250, 250)); d.rectangle((0, 2 * h // 3, w, h), fill=(8, 8, 8))
    def star(cx, cy, R, r=None):
        r = r or R * 0.382; pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5; rr = R if i % 2 == 0 else r; pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=(206, 17, 38))
    for k in (-1, 0, 1): star(w / 2 + k * w * 0.2, h / 2, h * 0.12)
    a = arr(f); yy, xx = np.mgrid[0:h, 0:w]
    # wave: vertical displacement + lighting
    ph = xx / w * 2 * math.pi * 1.35
    disp = (np.sin(ph) * 38 + np.sin(ph * 2.1 + 1) * 9) * (0.25 + 0.75 * xx / w)
    ys = np.clip(yy + disp, 0, h - 1).astype(int)
    out = a[ys, xx]
    shade = 1 + 0.38 * np.cos(ph + 0.4) * (0.4 + 0.6 * xx / w) + 0.1 * np.cos(ph * 2.1 + 1)
    out = out * shade[..., None]
    alpha = np.ones((h, w), "float32")
    ys_edge = (yy - disp)  # which pixels are inside after displacement
    alpha = ((ys_edge >= 0) & (ys_edge <= h - 1)).astype("float32")
    rgba = np.dstack([np.clip(out, 0, 1), alpha])
    return Image.fromarray((rgba * 255).astype("uint8"), "RGBA")

def build(pdir, out):
    P = lambda n: Image.open(os.path.join(pdir, n)).convert("RGB")
    # 1 ---- city background (cool, dark, slightly blurred = depth of field)
    city = cover(P("00.jpg"), W, H).filter(ImageFilter.GaussianBlur(2.2))
    a = arr(city); lum = a.mean(2, keepdims=True)
    a = lum * 0.55 + a * 0.45; a = tint(a, (0.62, 0.78, 1.0)) * 1.25
    sky = grad_mask(W, H, lambda x, y: 1 - y * 2.2); a = a * (1 - 0.45 * sky[..., None]) + np.array((0.04, 0.08, 0.22)) * 0.45 * sky[..., None]
    base = a
    # 2 ---- warm sunrise glow behind the crowd
    glow = grad_mask(W, H, lambda x, y: 1.0 - np.sqrt(((x - 0.38) / 0.65) ** 2 + ((y - 0.72) / 0.55) ** 2))
    base = screen(base, np.array((1.0, 0.45, 0.10)) * (glow ** 1.3 * 0.95)[..., None])
    # 3 ---- big crowd (Hama), warm graded, feathered into the scene
    cr = P("01.jpg"); cr = cr.crop((0, int(cr.height * 0.18), cr.width, cr.height)); cr = cover(cr, 1500, 1010).filter(ImageFilter.UnsharpMask(2, 90, 3))
    ca = arr(cr); ca = (ca - 0.5) * 1.25 + 0.5; ca = tint(ca, (1.22, 1.02, 0.84)) * 1.12
    cm = np.zeros((H, W), "float32")
    local = grad_mask(1500, 1010, lambda x, y: smooth((y - 0.10) / 0.40) * smooth((1 - x) / 0.38 + 0.0) * 1.0)
    # left edge hard bleed, right fade
    cm[H - 1010:, :1500] = local
    full = np.zeros((H, W, 3), "float32"); full[H - 1010:, :1500] = ca
    base = layer_over(base, full, cm * 1.0)
    # 4 ---- second crowd texture (Assi square) screened low for density
    c2 = cover(P("07.jpg"), 1100, 520); c2a = tint(arr(c2), (1.1, 0.95, 0.8))
    m2 = np.zeros((H, W), "float32"); m2[H - 520:, 0:1100] = grad_mask(1100, 520, lambda x, y: smooth(y / 0.5) * smooth((1 - x) / 0.35)) * 0.55
    f2 = np.zeros((H, W, 3), "float32"); f2[H - 520:, 0:1100] = c2a
    pass  # second crowd layer removed (messy seam)
    # 5 ---- hero flag (generated, waved), with shadow + backlight
    fl = flag(); fl = fl.rotate(9, expand=True, resample=Image.BICUBIC); fl = fl.resize((int(fl.width * 0.60), int(fl.height * 0.60)), Image.LANCZOS)
    sh = Image.new("L", (W, H), 0); sh.paste(fl.split()[3].point(lambda v: int(v * 0.8)), (-60, 50))
    sh = sh.filter(ImageFilter.GaussianBlur(26)); base = base * (1 - 0.6 * np.asarray(sh, "float32")[..., None] / 255)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lay.paste(fl, (-80, 30))
    la = np.asarray(lay, "float32") / 255
    base = layer_over(base, la[..., :3], la[..., 3])
    rim = np.asarray(lay.split()[3].filter(ImageFilter.GaussianBlur(14)), "float32") / 255
    base = screen(base, np.array((1.0, 0.8, 0.4)) * (rim * 0.22)[..., None])
    # 6 ---- light: anamorphic streak + rays
    yy, xx = np.mgrid[0:H, 0:W]
    streak = np.exp(-((yy - 0.60 * H) / 5.0) ** 2) * np.exp(-((xx - 0.30 * W) / 900) ** 2)
    base = screen(base, np.array((1.0, 0.7, 0.35)) * (streak * 0.55)[..., None])
    ray = np.zeros((H, W), "float32")
    for ang, wd, amp in ((-0.55, 0.05, 0.5), (-0.30, 0.035, 0.4), (-0.10, 0.07, 0.35), (0.12, 0.04, 0.3)):
        th = np.arctan2(yy - 0.62 * H, xx - 0.30 * W); ray += amp * np.exp(-((th - (ang - 1.7)) / wd) ** 2) * np.clip(1 - np.hypot(xx - 0.30 * W, yy - 0.62 * H) / 1400, 0, 1)
    base = screen(base, np.array((1.0, 0.75, 0.4)) * (ray * 0.25)[..., None])
    # 7 ---- dark gradient on the right for text legibility
    rt = grad_mask(W, H, lambda x, y: smooth((x - 0.48) / 0.45)); base = base * (1 - 0.55 * rt[..., None]) + np.array((0.03, 0.02, 0.05)) * 0.55 * rt[..., None]
    B = img(base).convert("RGBA")
    # 8 ---- typography
    def gradient_fill(mask, c_top, c_bot, y0, y1):
        g = np.zeros((H, W, 3), "float32")
        t = np.clip((np.arange(H) - y0) / (y1 - y0), 0, 1)[:, None, None]
        g[:] = np.array(c_top) * (1 - t) + np.array(c_bot) * t
        return Image.fromarray((g * 255).astype("uint8")), mask
    def draw_title(B, txt, y, sz, c_top, c_bot, x=1850):
        m = text_mask(txt, (x, y), sz); ms = text_mask(txt, (x, y), sz, stroke=22)
        sh = ms.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.9)); shl = Image.new("RGBA", (W, H), (0, 0, 0, 255)); shl.putalpha(ImageChops.offset(sh, 10, 18)); B = Image.alpha_composite(B, shl)
        outline = Image.new("RGBA", (W, H), (12, 8, 8, 255)); outline.putalpha(ms); B = Image.alpha_composite(B, outline)
        bl = Image.new("RGBA", (W, H), (255, 255, 255, 255)); bl.putalpha(text_mask(txt, (x, y), sz, stroke=26).filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.12)))
        gf, _ = gradient_fill(m, c_top, c_bot, y + sz * 0.1, y + sz * 1.05); gl = gf.convert("RGBA"); gl.putalpha(m); B = Image.alpha_composite(B, gl)
        hi = Image.new("RGBA", (W, H), (255, 255, 255, 0)); hm = ImageChops.multiply(m, Image.fromarray((np.clip((np.arange(H) - y) / (sz * 0.35), 0, 1)[::-1][:, None].repeat(W, 1) * 0 + 0).astype("uint8")))
        return B
    B = draw_title(B, "الثورة", 20, 340, (1.0, 0.93, 0.35), (1.0, 0.52, 0.04))
    B = draw_title(B, "السورية", 385, 285, (1.0, 1.0, 1.0), (0.78, 0.84, 0.95))
    # red banner + year chip
    d = ImageDraw.Draw(B)
    bx0, by0, bx1, by1 = 820, 850, 1860, 1005
    ban = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(ban)
    bd.polygon([(bx0 + 40, by0), (bx1, by0), (bx1, by1), (bx0, by1)], fill=(214, 24, 36, 255))
    sh = ban.split()[3].filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.7)); shl = Image.new("RGBA", (W, H), (0, 0, 0, 255)); shl.putalpha(ImageChops.offset(sh, 6, 12))
    B = Image.alpha_composite(B, shl); B = Image.alpha_composite(B, ban); d = ImageDraw.Draw(B)
    d.polygon([(bx0 + 40, by0), (bx1, by0), (bx1, by1), (bx0, by1)], outline=(255, 255, 255, 255), width=5)
    d.text(((bx0 + 40 + bx1) / 2, (by0 + by1) / 2 - 4), "القصة الكاملة 2011 - 2024", font=font(80), fill=(255, 255, 255), anchor="mm", direction="rtl", language="ar", stroke_width=3, stroke_fill=(90, 0, 8))
    # 9 ---- finishing: bloom, S-curve, vignette, grain
    f = arr(B.convert("RGB"))
    hi = np.clip(f - 0.72, 0, 1) * 3; bloom = arr(img(hi).filter(ImageFilter.GaussianBlur(30))); f = screen(f, bloom * 0.55)
    f = smooth(f) * 0.55 + f * 0.45; f = (f - 0.5) * 1.1 + 0.5
    lumf = f.mean(2, keepdims=True); f = lumf + (f - lumf) * 1.18
    v = grad_mask(W, H, lambda x, y: np.sqrt(((x - 0.5) / 0.75) ** 2 + ((y - 0.5) / 0.85) ** 2) - 0.45); f = f * (1 - 0.55 * np.clip(v, 0, 1)[..., None])
    f = f + rng.normal(0, 0.012, f.shape).astype("float32")
    img(f).save(out); print("saved", out)

if __name__ == "__main__": build(sys.argv[1], sys.argv[2])
