"""Real footage (Wikimedia Commons, free licences): download, edit into 1280x600 cut-aways with credit captions."""
import hashlib, json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import commons as C
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from textutil import S, font, draw_text, text_w

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "build_tmp", "footage")
W, H, FPS = 1280, 600, 24


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    return r.stdout


def probe(path):
    try:
        return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]).strip())
    except Exception:
        return 0.0


def meta(title):
    d = C._get({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1600})
    p = d["query"]["pages"][0]
    ii = (p.get("imageinfo") or [None])[0]
    if not ii: return None
    md = ii.get("extmetadata", {})
    return {"url": ii["url"], "thumb": ii.get("thumburl") or ii["url"], "w": ii.get("width"), "h": ii.get("height"),
            "license": C._strip(md.get("LicenseShortName", {}).get("value", "")),
            "artist": C._strip(md.get("Artist", {}).get("value", ""))[:60] or "Wikimedia Commons",
            "page": ii.get("descriptionurl")}


def fetch(item):
    """Download media for an item -> adds item['path'], item['license'], item['artist']. Returns False on failure."""
    os.makedirs(TMP, exist_ok=True)
    key = hashlib.md5(item["title"].encode()).hexdigest()[:10]
    try:
        m = meta(item["title"])
        if not m: return False
        item.update({k: m[k] for k in ("license", "artist", "page")})
        if item["kind"] == "photo":
            path = os.path.join(TMP, key + ".jpg")
            if not os.path.exists(path):
                tmp = path + ".dl"; C.download(m["thumb"], tmp)
                Image.open(tmp).convert("RGB").save(path, quality=92); os.remove(tmp)
        else:
            dur, ders = C.video_derivatives(item["title"])
            cands = [x for x in ders if x.get("src")]
            def score(x):
                h = int(x.get("height") or 0)
                return (abs(h - 480) if h else 999, 0 if "mp4" in (x.get("type") or "") else 1)
            cands.sort(key=score)
            src = cands[0]["src"] if cands else m["url"]
            ext = os.path.splitext(src.split("?")[0])[1] or ".webm"
            path = os.path.join(TMP, key + ext)
            if not os.path.exists(path):
                C.download(src, path)
            if probe(path) <= 0: return False
        item["path"] = path
        return True
    except Exception as e:
        print("  footage skip:", item["title"], "->", str(e)[:160])
        return False


def _latin(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def caption_png(item, out):
    """Transparent lower-third: Arabic caption + credit line."""
    img = Image.new("RGBA", (W * 2, 64 * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W * 2, 64 * 2], fill=(0, 0, 0, 150))
    f1 = font(24)
    f2 = _latin(15 * 2)
    draw_text(d, (W * 2 - 40, 22 * 2), "لقطة حقيقية: " + item.get("cap", ""), f1, (255, 255, 255), "rm")
    cr = f"{item.get('artist', '')} | {item.get('license', '')} | Wikimedia Commons"
    d.text((W * 2 - 40, 49 * 2), cr, font=f2, fill=(210, 210, 210), anchor="rm")
    img.resize((W, 64), Image.LANCZOS).save(out)


def photo_base(path, out):
    """Blurred backdrop + fitted photo, 1600x750 (room for Ken Burns)."""
    im = Image.open(path).convert("RGB"); tw, th = 1600, 750
    bg = im.copy(); r = max(tw / bg.width, th / bg.height)
    bg = bg.resize((int(bg.width * r) + 1, int(bg.height * r) + 1)); l, t = (bg.width - tw) // 2, (bg.height - th) // 2
    bg = bg.crop((l, t, l + tw, t + th)).filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.55))
    r = min(tw / im.width, th / im.height); fg = im.resize((max(2, int(im.width * r)), max(2, int(im.height * r))), Image.LANCZOS)
    bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2)); bg.save(out, quality=94)


def make_clip(item, dur, out, seed=0):
    """Render one cut-away mp4 (no audio) with fade in/out and credit caption."""
    cap = out + ".cap.png"; caption_png(item, cap)
    fade = f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.1, dur - 0.35):.2f}:d=0.35"
    if item["kind"] == "photo":
        base = out + ".base.jpg"; photo_base(item["path"], base)
        n = int(dur * FPS) + 2
        zin = seed % 2 == 0
        z = f"'1+0.18*on/{n}'" if zin else f"'1.18-0.18*on/{n}'"
        vf = (f"[0:v]zoompan=z={z}:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={n}:s={W}x{H}:fps={FPS},"
              f"eq=saturation=0.92:contrast=1.04,{fade}[v];[v][1:v]overlay=0:{H - 64}[o]")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", base, "-i", cap, "-filter_complex", vf, "-map", "[o]", "-t", f"{dur:.2f}"]
    else:
        vd = probe(item["path"]); ss = 0.8 if vd > dur + 2 else 0.0
        vf = (f"[0:v]fps={FPS},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=22,eq=brightness=-0.15[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,eq=saturation=0.92:contrast=1.05,{fade}[v];"
              f"[v][1:v]overlay=0:{H - 64}[o]")
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-ss", f"{ss}", "-i", item["path"], "-i", cap, "-filter_complex", vf, "-map", "[o]", "-t", f"{dur:.2f}"]
    run(cmd + ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out])
