"""Arabic text helpers (Pillow + libraqm does shaping and bidi)."""
import os
from PIL import ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(ROOT, "assets", "NotoSansArabic-Bold.ttf")
S = 2  # supersampling factor used by the whole renderer
_cache = {}

def font(size):
    """size in design pixels (1280x720 space); returns font scaled by S."""
    k = round(size * S)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(FONT_PATH, k)
    return _cache[k]

def draw_text(d, xy, text, f, fill, anchor="mm"):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, direction="rtl", language="ar")

def text_w(d, text, f):
    return d.textlength(text, font=f, direction="rtl", language="ar")

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(d, t, f) <= maxw:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines
