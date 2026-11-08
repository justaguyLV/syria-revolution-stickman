"""Sound design for the video, 100 % procedural (numpy/scipy) + TTS crowd chants.

`render(scenes, starts, total, tmp)` reads each scene's "events" (data/sfx.json), synthesises every sound and writes
build_tmp/sfx.wav (mono 44.1 kHz). The same events drive the on-screen effects (muzzle flashes, blasts, shake).
"""
import asyncio, os, subprocess, random
import numpy as np
from scipy import signal

SR = 44100
_rng = np.random.default_rng(7)

# ------------------------------------------------------------------ DSP helpers
def noise(n): return _rng.standard_normal(n).astype(np.float32)
def tt(n): return np.arange(n, dtype=np.float32) / SR

def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos"), x).astype(np.float32)

def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x).astype(np.float32)

def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x).astype(np.float32)

def env(n, tau): return np.exp(-tt(n) / tau).astype(np.float32)

def norm(x, peak=0.95):
    m = float(np.max(np.abs(x))) or 1.0
    return (x / m * peak).astype(np.float32)

_ir_cache = {}
def reverb(x, rt=0.6, wet=0.3, pre=0.012):
    key = round(rt, 2)
    if key not in _ir_cache:
        n = int(SR * rt * 1.2)
        ir = noise(n) * np.exp(-tt(n) * (6.9 / rt))
        ir = lp(ir, 6000)
        ir[: int(SR * pre)] = 0
        _ir_cache[key] = (ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)).astype(np.float32)
    wetsig = signal.fftconvolve(x, _ir_cache[key])[: len(x) + int(SR * rt)]
    out = np.zeros(len(wetsig), np.float32)
    out[: len(x)] += x * (1 - wet * 0.5)
    out += wetsig.astype(np.float32) * wet * 2.2
    return out

def sine_sweep(f0, f1, n):
    f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)

# ------------------------------------------------------------------ sound generators
_cache = {}
def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]

def gunshot(seed=0, dist=False):
    def make():
        n = int(SR * 0.9)
        crack = hp(noise(n), 1800) * env(n, 0.009)
        body = lp(noise(n), 1400) * env(n, 0.045)
        thump = sine_sweep(150, 55, n) * env(n, 0.05)
        x = crack * 1.0 + body * 0.9 + thump * 0.7
        x = np.tanh(x * 1.6)
        x = reverb(x, rt=0.5 + 0.1 * (seed % 3), wet=0.32)
        if dist:
            x = lp(x, 2200) * 0.55
            x = reverb(x, rt=1.4, wet=0.45)
        return norm(x, 0.9)
    return _cached(("gun", seed % 5, dist), make)

def burst(n_shots, gap=0.1, dist=False, vol=1.0):
    total = int(SR * (n_shots * gap + 1.4))
    out = np.zeros(total, np.float32)
    for i in range(n_shots):
        g = gunshot(random.randrange(5), dist)
        at = int(SR * (i * gap + random.uniform(-0.012, 0.012)))
        at = max(0, at)
        out[at: at + len(g)] += g[: total - at] * random.uniform(0.7, 1.0)
    return out * vol

def explosion(size=1.0, dist=False):
    def make():
        n = int(SR * (3.6 + size))
        t = tt(n)
        crack = hp(noise(n), 900) * env(n, 0.035)
        boom = lp(noise(n), 260) * env(n, 0.55 * size + 0.2)
        mid = lp(noise(n), 1200) * env(n, 0.22)
        sub = (sine_sweep(70, 32, n)) * env(n, 0.75 * size + 0.2)
        deb = np.zeros(n, np.float32)
        k = int(SR * 2.2)
        idx = (_rng.random(220) ** 1.8 * k + int(SR * 0.18)).astype(int)
        deb[idx] = _rng.random(220).astype(np.float32)
        deb = lp(deb, 3500) * env(n, 0.9) * 0.9
        x = crack * 0.7 + boom * 2.3 + mid * 0.8 + sub * 1.6 + deb * 0.5
        x = np.tanh(x * 1.3)
        x = reverb(x, rt=2.0, wet=0.3)
        if dist:
            x = lp(x, 900) * 0.7
        return norm(x, 0.98)
    return _cached(("boom", round(size, 1), dist), make)

def whistle(dur=1.0):
    def make():
        n = int(SR * dur)
        x = sine_sweep(2800, 900, n) * (np.linspace(0.05, 1, n) ** 1.6)
        x += 0.4 * bp(noise(n), 1500, 4000) * np.linspace(0, 1, n)
        return norm(x * 0.5, 0.5)
    return _cached(("whistle", dur), make)

def jet(dur=5.0):
    def make():
        n = int(SR * dur)
        t = np.linspace(0, 1, n)
        bell = np.exp(-((t - 0.5) / 0.22) ** 2).astype(np.float32)
        x = bp(noise(n), 200, 1800) * bell
        x += lp(noise(n), 160) * bell * 1.8
        pitch = np.sin(2 * np.pi * np.cumsum(520 - 260 * t) / SR).astype(np.float32) * 0.05 * bell
        return norm(x + pitch, 0.8)
    return _cached(("jet", dur), make)

def siren(dur=8.0, dist=True):
    def make():
        n = int(SR * dur)
        t = tt(n)
        f = 640 + 260 * np.sin(2 * np.pi * t / 7.0 - 1.57)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
        x = x.astype(np.float32) * np.minimum(1, np.minimum(t, dur - t) / 1.5)
        x = reverb(lp(x, 2500), rt=1.6, wet=0.5)
        return norm(x, 0.5)
    return _cached(("siren", dur), make)

def rumble(dur=8.0):
    def make():
        n = int(SR * dur)
        t = tt(n)
        x = lp(noise(n), 55, 3) * (0.6 + 0.4 * lp(noise(n), 4)) * 40
        x += lp(noise(n), 140) * (np.abs(lp(noise(n), 6)) * 12)
        x *= np.minimum(1, np.minimum(t / 1.2, (dur - t) / 2.0))
        creak = np.zeros(n, np.float32)
        for _ in range(int(dur * 1.2)):
            a = int(_rng.random() * (n - SR))
            m = int(SR * _rng.uniform(0.15, 0.5))
            c = bp(noise(m), 400, 1400) * np.hanning(m) * _rng.uniform(0.1, 0.35)
            creak[a: a + m] += c
        return norm(x + creak * 0.9, 0.85)
    return _cached(("rumble", dur), make)

def murmur(dur, level=1.0):
    n = int(SR * dur)
    x = np.zeros(n, np.float32)
    for lo, hi in ((180, 600), (500, 1500), (1200, 3200)):
        band = bp(noise(n), lo, hi)
        am = 0.55 + 0.45 * lp(noise(n), _rng.uniform(3, 7)) * 6
        x += band * np.clip(am, 0.05, 1.5)
    t = tt(n)
    x *= np.minimum(1, np.minimum(t / 1.0, (dur - t) / 1.0))
    return norm(x, 0.5 * level)

def roar(dur, level=1.0):
    n = int(SR * dur)
    t = tt(n)
    swell = np.minimum(1, t / (dur * 0.25)) * np.minimum(1, (dur - t) / (dur * 0.35))
    x = np.zeros(n, np.float32)
    for f0, bw in ((700, 260), (1200, 400), (2600, 700), (420, 150)):
        wob = 0.6 + 0.4 * np.sin(2 * np.pi * (0.7 + _rng.random() * 1.5) * t + _rng.random() * 6)
        x += bp(noise(n), f0 - bw / 2, f0 + bw / 2) * wob
    return norm(x * swell, 0.7 * level)

def applause(dur, level=1.0):
    n = int(SR * dur)
    x = np.zeros(n, np.float32)
    k = int(dur * 380)
    x[(_rng.random(k) * n).astype(int)] = _rng.random(k).astype(np.float32)
    x = hp(lp(x, 7000), 1000) * 40
    x = lp(x, 6000) + 0.5 * bp(noise(n), 800, 3000) * 0.25
    t = tt(n)
    x *= np.minimum(1, np.minimum(t / 0.8, (dur - t) / 1.2))
    return norm(x, 0.55 * level)

def firework(kind=0):
    def make():
        n = int(SR * 3.0)
        whoosh = bp(noise(int(SR * 0.7)), 600, 3500) * np.linspace(0.05, 1, int(SR * 0.7)) ** 2
        whoosh = np.concatenate([whoosh * 0.35, np.zeros(n - len(whoosh), np.float32)])
        pop_at = int(SR * 0.7)
        pop = np.zeros(n, np.float32)
        m = n - pop_at
        pop[pop_at:] = (hp(noise(m), 300) * env(m, 0.05) + lp(noise(m), 200) * env(m, 0.2) * 1.4)
        crack = np.zeros(n, np.float32)
        k = 160
        crack[(pop_at + _rng.random(k) ** 2 * SR * 1.6).astype(int)] = _rng.random(k).astype(np.float32)
        crack = hp(lp(crack, 6000), 1500) * 6 * env(n, 1.0)
        x = reverb(whoosh + pop * 0.9 + crack * 0.35, rt=1.6, wet=0.3)
        return norm(x, 0.7)
    return _cached(("fw", kind % 3), make)

def tank(dur=8.0):
    def make():
        n = int(SR * dur)
        t = tt(n)
        base = signal.sawtooth(2 * np.pi * 34 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 13 * t))
        x = lp(base.astype(np.float32), 160, 3) * 1.2
        clank = np.zeros(n, np.float32)
        step = int(SR / 9)
        for i in range(0, n - 2000, step):
            clank[i: i + 1500] += bp(noise(1500), 700, 2800) * np.exp(-np.arange(1500) / 260) * 0.35
        x += clank + lp(noise(n), 300) * 0.25
        x *= np.minimum(1, np.minimum(t / 1.5, (dur - t) / 1.5))
        return norm(x, 0.6)
    return _cached(("tank", dur), make)

def drone(dur):
    n = int(SR * dur)
    t = tt(n)
    x = sum(np.sin(2 * np.pi * f * t + p) for f, p in ((55, 0), (58.3, 1), (110.6, 2), (164.9, 0.5))) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.09 * t))
    x = x.astype(np.float32) * np.minimum(1, np.minimum(t / 2, (dur - t) / 2))
    return norm(x, 0.4)

def wind(dur, level=1.0):
    n = int(SR * dur)
    t = tt(n)
    x = lp(noise(n), 700) * (0.4 + 0.6 * np.abs(lp(noise(n), 0.4)) * 6)
    x *= np.minimum(1, np.minimum(t / 1.5, (dur - t) / 1.5))
    return norm(x, 0.35 * level)

def waves(dur, level=1.0):
    n = int(SR * dur)
    t = tt(n)
    sw = 0.5 + 0.5 * np.sin(2 * np.pi * 0.14 * t)
    x = (lp(noise(n), 900) * sw ** 2 + hp(lp(noise(n), 4000), 1500) * sw ** 3 * 0.4)
    x *= np.minimum(1, np.minimum(t / 1.5, (dur - t) / 1.5))
    return norm(x, 0.35 * level)

def birds(dur):
    n = int(SR * dur)
    out = np.zeros(n, np.float32)
    for _ in range(int(dur * 1.6)):
        a = int(_rng.random() * (n - SR))
        for k in range(_rng.integers(2, 6)):
            m = int(SR * _rng.uniform(0.05, 0.11))
            f0 = _rng.uniform(2800, 5200)
            c = sine_sweep(f0, f0 * _rng.uniform(0.7, 1.4), m) * np.hanning(m) * 0.22
            s = a + int(k * SR * 0.12)
            out[s: s + m] += c[: max(0, min(m, n - s))]
    return out

def whoosh(dur=0.9):
    n = int(SR * dur)
    return norm(bp(noise(n), 400, 2500) * np.sin(np.linspace(0, np.pi, n)) ** 2, 0.5)

# ------------------------------------------------------------------ chants (TTS crowd)
CHANTS = {
    "wants": "الشعب يريد إسقاط النظام",
    "gsf": "الله، سوريا، حرية وبس",
    "freedom": "حرية، حرية، حرية",
    "one": "واحد، واحد، واحد، الشعب السوري واحد",
    "peaceful": "سلمية، سلمية، سلمية",
    "dignity": "الشعب السوري ما بينذل",
    "allahu": "الله أكبر",
    "free": "سوريا حرة، حرة",
}
VOICES = ["ar-SY-LaithNeural", "ar-SY-AmanyNeural", "ar-SA-HamedNeural", "ar-EG-ShakirNeural",
          "ar-JO-TaimNeural", "ar-LB-RamiNeural", "ar-IQ-BasselNeural", "ar-SA-ZariyahNeural"]
_chant_audio = {}          # phrase -> [np arrays]


async def _tts_one(sem, text, voice, out):
    import edge_tts
    async with sem:
        for a in range(3):
            try:
                await edge_tts.Communicate(text, voice, rate="+6%").save(out)
                return True
            except Exception:
                await asyncio.sleep(1.5 * (a + 1))
    return False


def _decode(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def prepare_chants(tmp, phrases):
    if os.environ.get("NO_TTS") == "1":
        return
    d = os.path.join(tmp, "chants"); os.makedirs(d, exist_ok=True)

    async def go():
        sem = asyncio.Semaphore(6); jobs = []
        for ph in phrases:
            for v in VOICES:
                out = os.path.join(d, f"{ph}_{v}.mp3")
                if not os.path.exists(out):
                    jobs.append(_tts_one(sem, CHANTS[ph], v, out))
        res = await asyncio.gather(*jobs)
        print(f"chants: {sum(res)}/{len(res)} voice clips ready", flush=True)
    asyncio.run(go())
    for ph in phrases:
        arrs = []
        for v in VOICES:
            p = os.path.join(d, f"{ph}_{v}.mp3")
            if os.path.exists(p) and os.path.getsize(p) > 500:
                a = _decode(p)
                nz = np.where(np.abs(a) > 0.02)[0]
                if len(nz) > 100:
                    a = a[nz[0]: nz[-1] + 1]            # trim silence
                    arrs.append(a / (np.max(np.abs(a)) + 1e-9))
        _chant_audio[ph] = arrs


def chant_once(phrase, level=1.0, crowd=8):
    """Layer many pitch/speed-shifted voices with tiny timing offsets -> a shouting crowd."""
    voices = _chant_audio.get(phrase) or []
    if not voices:                                         # TTS unavailable: crowd roar fallback
        return roar(1.1, 0.8 * level)
    longest = max(len(v) for v in voices)
    out = np.zeros(int(longest * 1.25) + SR // 4, np.float32)
    for i in range(crowd):
        v = voices[i % len(voices)]
        sp = _rng.uniform(0.92, 1.12)
        idx = np.arange(0, len(v) - 1, sp)
        shifted = np.interp(idx, np.arange(len(v)), v).astype(np.float32)
        shifted = hp(shifted, 140)
        off = int(_rng.uniform(0, 0.11) * SR)
        out[off: off + len(shifted)] += shifted * _rng.uniform(0.55, 1.0)
    out = np.tanh(out * 0.55) * 1.2                       # glue / soft clip = shouting
    out = bp(out, 180, 5200) * 1.0
    out = reverb(out, rt=0.9, wet=0.35)
    out += roar(len(out) / SR, 0.22) [: len(out)] if len(out) / SR > 0.5 else 0
    return norm(out, 0.8 * level)


def chant(phrase, reps=3, period=2.0, level=1.0, crowd=8):
    """`reps` shouted repetitions, one every `period` seconds (same rhythm as the on-screen bubble)."""
    parts = [(int(r * period * SR), chant_once(phrase, level * (0.85 + 0.15 * (r % 2)), crowd)) for r in range(reps)]
    out = np.zeros(parts[-1][0] + len(parts[-1][1]), np.float32)
    for at, c in parts:
        out[at: at + len(c)] += c
    return out


# ------------------------------------------------------------------ master render
def _place(master, snd, at, vol=1.0, pan=None):
    a = int(at * SR)
    if a >= len(master) or a + len(snd) <= 0:
        return
    s0 = max(0, -a)
    seg = snd[s0:]
    a = max(0, a)
    m = min(len(seg), len(master) - a)
    master[a: a + m] += seg[:m] * vol


def render(scenes, starts, total, tmp, events_key="events"):
    random.seed(3)
    master = np.zeros(int((total + 6) * SR), np.float32)
    phrases = sorted({e["phrase"] for sc in scenes for e in sc.get(events_key, []) if e["type"] == "chant"})
    prepare_chants(tmp, phrases)
    for i, sc in enumerate(scenes):
        t0 = starts[i]; dur = sc["_dur"]
        for e in sc.get(events_key, []):
            ty = e["type"]; at = t0 + e["t"]; vol = e.get("vol", 1.0)
            if ty == "shot":
                _place(master, burst(e.get("n", 3), e.get("gap", 0.1), e.get("dist", False)), at, 0.55 * vol)
            elif ty in ("blast", "shell"):
                dist = e.get("dist", False)
                if ty == "shell":
                    _place(master, whistle(e.get("lead", 1.0)), at - e.get("lead", 1.0), 0.5 * vol)
                _place(master, explosion(e.get("size", 1.0), dist), at, 0.85 * vol)
            elif ty == "jet":
                _place(master, jet(e.get("dur", 5.0)), at, 0.55 * vol)
            elif ty == "siren":
                _place(master, siren(e.get("dur", 8.0)), at, 0.4 * vol)
            elif ty == "rumble":
                _place(master, rumble(e.get("dur", 8.0)), at, 0.8 * vol)
            elif ty == "tank":
                _place(master, tank(e.get("dur", 8.0)), at, 0.5 * vol)
            elif ty == "chant":
                _place(master, chant(e["phrase"], e.get("reps", 3), e.get("period", 2.0), 1.0, e.get("crowd", 8)), at, 0.55 * vol)
            elif ty == "cheer":
                _place(master, roar(e.get("dur", 4.0)), at, 0.5 * vol)
            elif ty == "applause":
                _place(master, applause(e.get("dur", 5.0)), at, 0.5 * vol)
            elif ty == "firework":
                _place(master, firework(e.get("k", 0)), at - 0.7, 0.55 * vol)
            elif ty == "murmur":
                _place(master, murmur(e.get("dur", dur - e["t"]), 1.0), at, 0.28 * vol)
            elif ty == "drone":
                _place(master, drone(e.get("dur", dur - e["t"])), at, 0.3 * vol)
            elif ty == "wind":
                _place(master, wind(e.get("dur", dur - e["t"])), at, 0.5 * vol)
            elif ty == "waves":
                _place(master, waves(e.get("dur", dur - e["t"])), at, 0.5 * vol)
            elif ty == "birds":
                _place(master, birds(e.get("dur", dur - e["t"])), at, 0.5 * vol)
            elif ty == "whoosh":
                _place(master, whoosh(), at, 0.5 * vol)
    peak = float(np.max(np.abs(master))) or 1
    master = np.tanh(master / max(peak, 1.0) * 1.1) * 0.9
    out = os.path.join(tmp, "sfx.wav")
    import wave
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(master, -1, 1) * 32767).astype(np.int16).tobytes())
    return out
