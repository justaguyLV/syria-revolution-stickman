"""Build the full video:  python src/build.py [--preview N] [--out out/syria.mp4]"""
import asyncio, json, os, re, subprocess, sys, argparse, shutil, multiprocessing as mp
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textutil import S, font, draw_text, text_w, wrap
import draw as D
import mapview as M
import footage as F
import fx
import sfx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1280, 720, 24
LEAD, TAIL = 0.7, 0.9           # silence before / after narration (s)
VOICE = os.environ.get("TTS_VOICE", "ar-SA-HamedNeural")
RATE = os.environ.get("TTS_RATE", "-4%")
TMP = os.path.join(ROOT, "build_tmp")

SCENES = json.load(open(os.path.join(ROOT, "data", "scenes.json"), encoding="utf-8"))
_SFX = json.load(open(os.path.join(ROOT, "data", "sfx.json"), encoding="utf-8"))
for _sc in SCENES:
    _sc["events"] = [dict(e) for e in _SFX.get(_sc["id"], [])]
SUBS = []          # per scene: list of (start, end, text) relative to scene start


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stderr[-2000:]); raise SystemExit(f"command failed: {' '.join(cmd[:3])}")
    return r.stdout


def probe(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]).strip())


async def _tts(text, out):
    import edge_tts
    last = None
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(out)
            return
        except Exception as e:      # network hiccup -> retry
            last = e; await asyncio.sleep(2 + attempt * 2)
    raise last


def make_audio():
    os.makedirs(TMP, exist_ok=True)
    silent = os.environ.get("NO_TTS") == "1"
    for i, sc in enumerate(SCENES):
        raw = os.path.join(TMP, f"v{i:02d}.mp3")
        if silent:
            dur = max(6.0, len(sc["narration"]) * 0.062)
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{dur:.2f}", "-q:a", "9", raw])
        elif not os.path.exists(raw):
            asyncio.run(_tts(sc["narration"], raw))
        nd = probe(raw)
        sc["_nar"] = nd
        sc["_dur"] = nd + LEAD + TAIL
        pad = os.path.join(TMP, f"p{i:02d}.wav")
        run(["ffmpeg", "-y", "-i", raw, "-af", f"adelay={int(LEAD*1000)}:all=1,apad=whole_dur={sc['_dur']:.3f}",
             "-ar", "44100", "-ac", "1", pad])
        print(f"scene {i:02d} {sc['id']:<11} narration {nd:5.1f}s")
    lst = os.path.join(TMP, "concat.txt")
    open(lst, "w").write("".join(f"file 'p{i:02d}.wav'\n" for i in range(len(SCENES))))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(TMP, "voice.wav")])


def split_subs(sc):
    text = sc["narration"]
    sents = [s.strip() for s in re.split(r"(?<=[.؟!])\s+", text) if s.strip()]
    chunks = []
    for s in sents:                      # break long sentences at commas
        parts = [p.strip() for p in re.split(r"(?<=،)\s+", s) if p.strip()]
        cur = ""
        for p in parts:
            if cur and len(cur) + len(p) > 78:
                chunks.append(cur); cur = p
            else:
                cur = (cur + " " + p).strip()
        if cur: chunks.append(cur)
    total = sum(len(c) for c in chunks)
    t = LEAD; out = []
    for c in chunks:
        dd = sc["_nar"] * len(c) / total
        out.append((t, t + dd, c)); t += dd
    return out


def make_music(total):
    out = os.path.join(TMP, "music.wav")
    run(["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"sine=f=110:d={total:.1f}", "-f", "lavfi", "-i", f"sine=f=164.81:d={total:.1f}",
         "-f", "lavfi", "-i", f"sine=f=207.65:d={total:.1f}", "-f", "lavfi", "-i", f"sine=f=277.18:d={total:.1f}",
         "-filter_complex", "[0][1][2][3]amix=inputs=4:normalize=0,tremolo=f=0.12:d=0.6,lowpass=f=700,volume=0.05,"
                            f"afade=t=in:d=3,afade=t=out:st={total-4:.1f}:d=4[m]",
         "-map", "[m]", "-ar", "44100", "-ac", "1", out])
    return out


# ----------------------------------------------------------------- rendering
STARTS = []

def locate(t):
    for i, sc in enumerate(SCENES):
        if t < STARTS[i] + sc["_dur"]:
            return i
    return len(SCENES) - 1


def render_frame(n):
    t = n / FPS
    i = locate(t)
    sc = SCENES[i]; lt = t - STARTS[i]
    prev = SCENES[i - 1] if i > 0 else None
    img = Image.new("RGB", (W * S, H * S), D.PAPER)
    d = ImageDraw.Draw(img)

    # --- map panel (right)
    k = min(1.0, lt / 1.6)
    vd = M.lerp_view(prev["view"], sc["view"], k) if prev else sc["view"]
    zk = min(1.0, lt / 1.2)
    M.draw_map(img, (440 * S, 18 * S, 1262 * S, 588 * S), vd, prev["era"] if prev else "none", sc["era"], zk, sc, lt, sc["_dur"])
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([440 * S, 18 * S, 1262 * S, 588 * S], radius=14 * S, outline=D.INK, width=int(3 * S))

    # --- left: date + title
    fade = min(1.0, lt / 0.5)
    draw_text(d, (210 * S, 52 * S), sc["date"], font(34 if len(sc["date"]) < 14 else 24), D.RED, "mm")
    draw_text(d, (210 * S, 100 * S), sc["title"], font(24), D.INK, "mm")
    d.line([(70 * S, 128 * S), (350 * S, 128 * S)], fill=D.INK, width=int(2 * S))

    # --- stage (own transparent canvas so it can shake + carry glows)
    stage = Image.new("RGBA", (440 * S, 606 * S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stage)
    D.CANVAS = stage
    D.STAGES[sc["stage"]](sd, t, lt, sc["_dur"], sc)
    for e in fx.events(sc, "blast", "shell"):
        if "stage" in e:
            fx.fireball(stage, e["stage"][0] * S, e["stage"][1] * S, lt - e["t"], 30 * S * e.get("size", 1.0) ** 0.6, seed=int(e["t"] * 10))
    sdx, sdy, flash = fx.shake(sc, lt)
    img.paste(stage, (int(sdx * S), int(sdy * S)), stage)
    d = ImageDraw.Draw(img)

    # --- subtitles
    d.rectangle([0, 606 * S, W * S, H * S], fill=(26, 26, 32))
    for (a, b, txt) in SUBS[i]:
        if a <= lt < b + 0.15:
            f = font(30)
            lines = wrap(d, txt, f, 1180 * S)
            y0 = 663 - (len(lines) - 1) * 21
            for j, ln in enumerate(lines[:3]):
                draw_text(d, (640 * S, (y0 + j * 42) * S), ln, f, (255, 255, 255), "mm")
            break
    # progress bar
    done = (t / TOTAL)
    d.rectangle([0, 600 * S, int(W * S * done), 606 * S], fill=D.RED)
    if flash > 0.02:
        img = Image.blend(img, Image.new("RGB", img.size, (255, 244, 220)), flash)
    return img.reduce(S).tobytes()



def sent_spans(sc):
    sents = [x.strip() for x in re.split(r"(?<=[.؟!])\s+", sc["narration"]) if x.strip()]
    total = sum(len(x) for x in sents); t = LEAD; out = []
    for x in sents:
        dd = sc["_nar"] * len(x) / total
        out.append((t, t + dd)); t += dd
    return out


def plan_broll():
    """-> list of (abs_start, dur, item) for every real-footage cut-away that could be fetched."""
    path = os.path.join(ROOT, "data", "broll.json")
    if not os.path.exists(path) or os.environ.get("NO_BROLL") == "1":
        return []
    data = json.load(open(path, encoding="utf-8")); plan = []
    for i, sc in enumerate(SCENES):
        spans = sent_spans(sc)
        groups = {}
        for it in data.get(sc["id"], []):
            groups.setdefault(min(it["sent"], len(spans) - 1), []).append(it)
        for k, items in groups.items():
            ok = [it for it in items if F.fetch(it)]
            if not ok: continue
            a, b = spans[k]; a += 0.25
            span = max(b - a, 2.6 * len(ok)); per = span / len(ok)
            for j, it in enumerate(ok):
                plan.append((STARTS[i] + a + j * per, min(per, 7.0), it))
    return plan


def compose(base, plan, out):
    """Overlay the real-footage cut-aways on the animated base video."""
    os.makedirs(os.path.join(TMP, "clips_b"), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", base]; chains = []; last = "0:v"
    for n, (t0, dur, it) in enumerate(plan):
        clip = os.path.join(TMP, "clips_b", f"b{n:03d}.mp4")
        F.make_clip(it, dur, clip, seed=n)
        cmd += ["-i", clip]
        chains.append(f"[{n + 1}:v]setpts=PTS-STARTPTS+{t0:.3f}/TB[c{n}];[{last}][c{n}]overlay=0:0:eof_action=pass:enable='between(t,{t0:.3f},{t0 + dur:.3f})'[o{n}]")
        last = f"o{n}"
    fc = os.path.join(TMP, "compose.txt"); open(fc, "w").write(";\n".join(chains))
    run(cmd + ["-filter_complex_script", fc, "-map", f"[{last}]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out])


TOTAL = 0.0

def main():
    global TOTAL
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "syria_revolution.mp4"))
    ap.add_argument("--preview", type=str, default="", help="scene ids to dump as PNG at mid-time, comma separated")
    a = ap.parse_args()
    make_audio()
    t = 0.0
    for sc in SCENES:
        STARTS.append(t); t += sc["_dur"]
        SUBS.append(split_subs(sc))
    TOTAL = t
    for sc in SCENES:
        for e in sc["events"]:
            if "t" not in e:
                e["t"] = round(e["f"] * sc["_dur"], 3)
    print(f"total {TOTAL:.1f}s = {TOTAL/60:.1f} min, frames {int(TOTAL*FPS)}")

    if a.preview:
        os.makedirs(os.path.join(ROOT, "out", "preview"), exist_ok=True)
        for sid in a.preview.split(","):
            i = next(k for k, s in enumerate(SCENES) if s["id"] == sid)
            n = int((STARTS[i] + SCENES[i]["_dur"] * 0.75) * FPS)
            Image.frombytes("RGB", (W, H), render_frame(n)).save(os.path.join(ROOT, "out", "preview", f"{sid}.png"))
            print("preview", sid)
        return

    music = make_music(TOTAL)
    sfx_wav = sfx.render(SCENES, STARTS, TOTAL, TMP)
    mixed = os.path.join(TMP, "mix.m4a")
    run(["ffmpeg", "-y", "-i", os.path.join(TMP, "voice.wav"), "-i", music, "-i", sfx_wav, "-filter_complex",
         "[0]asplit=2[v1][v2];[2]volume=1.0[s0];[s0][v2]sidechaincompress=threshold=0.03:ratio=2.2:attack=15:release=350:makeup=1[sd];"
         "[v1][1][sd]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "[a]", "-c:a", "aac", "-b:a", "192k", mixed])

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    nfr = int(TOTAL * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", mixed, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "copy", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    with mp.get_context("fork").Pool(os.cpu_count() or 2) as pool:
        for k, buf in enumerate(pool.imap(render_frame, range(nfr), chunksize=6)):
            ff.stdin.write(buf)
            if k % 480 == 0:
                print(f"frame {k}/{nfr}", flush=True)
    ff.stdin.close(); ff.wait()
    plan = plan_broll()
    if plan:
        print(f"composing {len(plan)} real-footage cut-aways ...", flush=True)
        final = a.out
        shutil.move(a.out, os.path.join(TMP, "base.mp4"))
        compose(os.path.join(TMP, "base.mp4"), plan, final)
        credits = [{"caption": it.get("cap"), "title": it["title"], "artist": it.get("artist"), "license": it.get("license"), "page": it.get("page")} for _, _, it in plan]
        json.dump(credits, open(os.path.join(os.path.dirname(a.out), "credits.json"), "w"), ensure_ascii=False, indent=1)
    print("done ->", a.out)


if __name__ == "__main__":
    main()
