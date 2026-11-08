"""Wikimedia Commons helper: search free-licensed videos/photos, fetch metadata, download."""
import json, re, time, urllib.parse, urllib.request, html

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "syria-stickman-video/1.0 (https://github.com/justaguyLV/syria-revolution-stickman; educational video)"}
BAD = re.compile(r"corpse|dead bod|killed|victim|massacre|torture|gore|mutilat|execut|beheading|wound|blood|casualt|martyr|body bag|naked|nude|porn", re.I)


def _get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(2 + 2 * a); err = e
    raise err


def _strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search(query, kind="video", limit=12):
    ft = "video" if kind == "video" else "bitmap"
    q = f"{query} filetype:{ft}"
    d = _get({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": limit,
              "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata|mediatype", "iiurlwidth": 480})
    out = []
    for p in d.get("query", {}).get("pages", []):
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        title = p["title"]
        desc = _strip(md.get("ImageDescription", {}).get("value", ""))[:200]
        if BAD.search(title) or BAD.search(desc):
            continue
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not re.search(r"CC|public domain|PD|GFDL|Attribution", lic, re.I):
            continue
        out.append({"title": title, "kind": kind, "w": ii.get("width"), "h": ii.get("height"), "mime": ii.get("mime"),
                    "url": ii.get("url"), "thumb": ii.get("thumburl"), "license": lic,
                    "artist": _strip(md.get("Artist", {}).get("value", ""))[:80], "desc": desc,
                    "page": ii.get("descriptionurl"), "index": p.get("index")})
    out.sort(key=lambda x: x.get("index") or 0)
    return out


def video_derivatives(title):
    """Small transcodes of a Commons video (the original can be huge)."""
    d = _get({"action": "query", "titles": title, "prop": "videoinfo", "viprop": "derivatives|url|size|duration"})
    pages = d.get("query", {}).get("pages", [])
    if not pages: return None, []
    vi = (pages[0].get("videoinfo") or [{}])[0]
    ders = [x for x in vi.get("derivatives", []) if x.get("src")]
    return vi.get("duration"), ders


def download(url, path):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(path, "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
            return
        except Exception as e:
            time.sleep(3 + 3 * a); err = e
    raise err
