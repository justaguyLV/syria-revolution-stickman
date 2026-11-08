"""YouTube thumbnail generator (1280x720) built from frames of the finished video.
Usage: python src/thumbnail.py video.mp4 out_dir
Needs: ffmpeg, Pillow (with raqm), numpy, scipy-free."""
import subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops

W, H = 1280, 720
FONT = os.path.join(os.path.dirname(__file__), "..", "assets", "NotoSansArabic-Bold.ttf")

def grab(video, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", out], check=True)
    return Image.open(out).convert("RGB")

def font(sz): return ImageFont.truetype(FONT, sz, layout_engine=ImageFont.Layout.RAQM)

def ar(draw_img, xy, text, sz, fill, stroke=0, stroke_fill=(0, 0, 0), anchor="ra"):
    d = ImageDraw.Draw(draw_img)
    d.text(xy, text, font=font(sz), fill=fill, anchor=anchor, direction="rtl", language="ar",
           stroke_width=stroke, stroke_fill=stroke_fill)

def glow(img, color, radius, strength=1.0, mask=None):
    """add a coloured blurred halo of a mask (L image) under img"""
    halo = Image.new("RGBA", img.size, color + (0,))
    a = mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    halo.putalpha(a)
    return Image.alpha_composite(img.convert("RGBA"), halo)

def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0]-1, im.size[1]-1), r, fill=255)
    out = im.convert("RGBA"); out.putalpha(m); return out

def cutout(im, bg=(246, 238, 224), tol=38):
    a = np.asarray(im.convert("RGB")).astype(int)
    dist = np.abs(a - np.array(bg)).sum(axis=2)
    alpha = np.clip((dist - tol) * 12, 0, 255).astype("uint8")
    out = im.convert("RGBA"); out.putalpha(Image.fromarray(alpha)); return out

def main(video, outdir):
    os.makedirs(outdir, exist_ok=True)
    f24 = grab(video, 315, os.path.join(outdir, "_f24.png"))   # 2024 offensive: map + green stickmen with flag
    # ---------- background ----------
    bg = Image.new("RGB", (W, H), (10, 14, 28))
    px = np.zeros((H, W, 3), "float32")
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - 860) / 700) ** 2 + ((yy - 340) / 520) ** 2)
    c0, c1 = np.array([150, 40, 30]), np.array([8, 10, 22])
    t = np.clip(d, 0, 1)[..., None]
    px = c0 * (1 - t) + c1 * t
    bg = Image.fromarray(px.astype("uint8")).convert("RGBA")
    # ---------- map ----------
    mp = f24.crop((445, 20, 1262, 585))
    mp = ImageEnhance.Contrast(ImageEnhance.Color(mp).enhance(1.45)).enhance(1.18)
    mp = mp.resize((int(mp.width * 1.1), int(mp.height * 1.1)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 110, 2))
    mp = rounded(mp, 34)
    mx, my = W - mp.width + 24, 40
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle((mx, my, mx+mp.width, my+mp.height), 34, fill=255)
    bg = glow(bg, (255, 190, 60), 38, 0.9, sh)          # warm halo
    bg = glow(bg, (0, 0, 0), 18, 1.0, sh.offset(0, 14) if hasattr(sh, "offset") else sh)
    bg.alpha_composite(mp, (mx, my))
    ImageDraw.Draw(bg).rounded_rectangle((mx, my, mx+mp.width-1, my+mp.height-1), 34, outline=(255, 220, 120, 255), width=5)
    # ---------- stickmen (colour-keyed from the frame) ----------
    st = cutout(f24.crop((0, 345, 430, 520)), tol=70)
    st = st.resize((int(st.width * 0.82), int(st.height * 0.82)), Image.LANCZOS)
    stm = st.split()[3]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); layer.alpha_composite(st, (14, 560))
    halo = Image.new("L", (W, H), 0); halo.paste(layer.split()[3], (0, 0))
    bg = glow(bg, (0, 0, 0), 6, 1.6, halo)
    bg.alpha_composite(layer)
    # ---------- vignette ----------
    v = np.clip((np.sqrt(((xx - W/2) / (W*0.75)) ** 2 + ((yy - H/2) / (H*0.9)) ** 2) - 0.55) * 1.2, 0, 0.75)
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0)); vig.putalpha(Image.fromarray((v * 255).astype("uint8")))
    bg = Image.alpha_composite(bg, vig)
    # ---------- text ----------
    # year ribbon
    rb = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(rb)
    rd.rounded_rectangle((28, 28, 330, 108), 18, fill=(215, 30, 40, 255), outline=(255, 255, 255, 255), width=4)
    bg.alpha_composite(rb)
    ar(bg, (180, 68), "2011 - 2024", 50, (255, 255, 255), anchor="mm")
    # main title
    for txt, y, col, sz in (("الثورة", 100, (255, 214, 40), 150), ("السورية", 240, (255, 255, 255), 126)):
        tmp = Image.new("L", (W, H), 0); ImageDraw.Draw(tmp).text((440, y), txt, font=font(sz), fill=255, anchor="ra", direction="rtl", language="ar", stroke_width=14)
        bg = glow(bg, (0, 0, 0), 10, 1.0, tmp)
        ar(bg, (440, y), txt, sz, col, stroke=12, stroke_fill=(10, 10, 10))
    # subtitle pill
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((30, 462, 440, 527), 14, fill=(255, 214, 40, 255), outline=(0, 0, 0, 255), width=4)
    bg.alpha_composite(pill)
    ar(bg, (235, 495), "بالخرائط والستيكمان", 44, (15, 15, 15), anchor="mm")
    out = bg.convert("RGB")
    out = ImageEnhance.Contrast(out).enhance(1.08)
    out.save(os.path.join(outdir, "thumbnail.png"))
    out.save(os.path.join(outdir, "thumbnail.jpg"), quality=95)
    os.remove(os.path.join(outdir, "_f24.png"))
    print("ok", os.path.getsize(os.path.join(outdir, "thumbnail.jpg")))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
