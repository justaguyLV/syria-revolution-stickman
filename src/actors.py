"""Stickman sprites rendered by the open-source engine vallahrich/stickman-mcp (SVG -> RGBA via cairosvg).
Clips are produced by tools/make_clips.mjs into build_tmp/clips/<name>/NNNN.svg"""
import io, os, re
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIP_DIR = os.environ.get("CLIP_DIR", os.path.join(ROOT, "build_tmp", "clips"))
FPS = 24
FIG_UNITS = 112.0          # figure height (ground -> top of head) in SVG units, at engine scale 1.0
GROUND_FROM_TOP = 236      # ground row inside the crop window (matches make_clips.mjs GY)
CW, CH = 220, 260
_svgs = {}
_cache = {}
POSE_TO_CLIP = {"stand": "idle", "walk": "walk", "run": "run", "fist": "jump", "hands_up": "jump",
                "sign": "idle", "jump": "jump", "wave": "wave", "point": "point", "sad": "stop"}


def available():
    return os.path.isdir(CLIP_DIR) and bool(os.listdir(CLIP_DIR))


def _load(name):
    if name not in _svgs:
        d = os.path.join(CLIP_DIR, name)
        _svgs[name] = [open(os.path.join(d, f), encoding="utf-8").read() for f in sorted(os.listdir(d))]
    return _svgs[name]


def _hex(c): return "#%02x%02x%02x" % tuple(c)


def frame(name, idx, px_per_unit, color, head_fill, stroke_mult=1.5):
    """RGBA sprite for clip frame `idx` (loops), scaled so the figure is FIG_UNITS*px_per_unit tall."""
    import cairosvg
    key = (name, idx, round(px_per_unit, 3), color, head_fill)
    if key in _cache:
        return _cache[key]
    svg = _load(name)[idx]
    svg = svg.replace("#202124", _hex(color))
    svg = re.sub(r'stroke-width="([\d.]+)"', lambda m: f'stroke-width="{float(m.group(1)) * stroke_mult:.2f}"', svg)
    svg = svg.replace('fill="#ffffff"', f'fill="{_hex(head_fill)}"')
    w = max(2, round(CW * px_per_unit))
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=w))).convert("RGBA")
    if len(_cache) > 4000:
        _cache.clear()
    _cache[key] = im
    return im


def paste(img, name, t, x, ground_y, height, color, head_fill, flip=1, phase=0.0, speed=1.0):
    """Paste the sprite so its feet stand on (x, ground_y); coordinates/height in output pixels."""
    n = len(_load(name))
    idx = int(((t * speed + phase) * FPS) % n)
    k = height / FIG_UNITS
    im = frame(name, idx, k, color, head_fill)
    if flip < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    gx = im.width / 2
    gy = GROUND_FROM_TOP * k
    img.alpha_composite(im, (int(x - gx), int(ground_y - gy))) if img.mode == "RGBA" else img.paste(im, (int(x - gx), int(ground_y - gy)), im)
