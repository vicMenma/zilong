"""
stream_extractor.py
Analyse un URL avec yt-dlp et propose à l'utilisateur
de choisir exactement quelle piste télécharger :
  - Vidéo  : résolution, fps, codec, taille
  - Audio  : langue, codec, bitrate, taille
  - Sous-titres : langue, format
"""
import logging
import yt_dlp
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# session par chat_id : { "url", "title", "video", "audio", "subs" }
_sessions: dict = {}
_pool = ThreadPoolExecutor(max_workers=2)


# ─── helpers ──────────────────────────────────

def _sz(b) -> str:
    """Octets → lisible."""
    if not b or b <= 0:
        return "?"
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {u}"
        b /= 1024
    return f"{b:.1f} GB"


_FLAGS = {
    "en":"🇬🇧","fr":"🇫🇷","de":"🇩🇪","es":"🇪🇸","pt":"🇵🇹",
    "it":"🇮🇹","ru":"🇷🇺","ja":"🇯🇵","ko":"🇰🇷","zh":"🇨🇳",
    "ar":"🇸🇦","hi":"🇮🇳","tr":"🇹🇷","nl":"🇳🇱","pl":"🇵🇱",
    "sv":"🇸🇪","da":"🇩🇰","fi":"🇫🇮","cs":"🇨🇿","uk":"🇺🇦",
    "ro":"🇷🇴","hu":"🇭🇺","el":"🇬🇷","he":"🇮🇱","th":"🇹🇭",
    "vi":"🇻🇳","id":"🇮🇩","ms":"🇲🇾","no":"🇳🇴",
}

def _flag(code: str) -> str:
    if not code:
        return "🌐"
    return _FLAGS.get(code.split("-")[0].lower()[:2], "🌐")


# ─── extraction (thread) ──────────────────────

def _fetch(url: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False) or {}


async def analyse(url: str, chat_id: int) -> dict | None:
    loop = get_event_loop()
    try:
        info = await loop.run_in_executor(_pool, _fetch, url)
    except Exception as e:
        logging.warning(f"[StreamExtractor] fetch error: {e}")
        return None

    if not info:
        return None

    formats   = info.get("formats") or []
    subtitles = info.get("subtitles") or {}

    # ── VIDEO ──────────────────────────────────
    videos = []
    for f in formats:
        vc = f.get("vcodec") or "none"
        ac = f.get("acodec") or "none"
        if vc == "none":
            continue                          # audio-only → skip here
        h   = f.get("height") or 0
        fps = int(f.get("fps") or 0)
        sz  = f.get("filesize") or f.get("filesize_approx") or 0
        vc_s = vc.split(".")[0]
        ac_s = ac.split(".")[0] if ac != "none" else "—"
        lang = f.get("language") or ""

        res = f"{h}p" if h else "?"
        if fps > 30:
            res += f" {fps}fps"
        audio_tag = f"+{ac_s}" if ac_s != "—" else " (no audio)"
        label = f"{_flag(lang)}  {res}  [{vc_s}{audio_tag}]  {_sz(sz)}"

        videos.append({
            "id": f.get("format_id", ""),
            "label": label,
            "h": h, "fps": fps,
            "sz": sz, "lang": lang,
            "ext": f.get("ext", "mp4"),
            "has_audio": ac != "none",
        })

    # trier par résolution desc, dédupliquer (1 entrée par hauteur×has_audio)
    videos.sort(key=lambda x: (x["h"], x["fps"]), reverse=True)
    seen_v, dedup_v = set(), []
    for v in videos:
        k = (v["h"], v["has_audio"])
        if k not in seen_v:
            seen_v.add(k)
            dedup_v.append(v)
    videos = dedup_v[:12]

    # ── AUDIO ──────────────────────────────────
    audios = []
    for f in formats:
        vc = f.get("vcodec") or "none"
        ac = f.get("acodec") or "none"
        if vc != "none" or ac == "none":
            continue                          # skip video or empty
        abr  = int(f.get("abr") or f.get("tbr") or 0)
        sz   = f.get("filesize") or f.get("filesize_approx") or 0
        lang = f.get("language") or ""
        ac_s = ac.split(".")[0]
        ext  = f.get("ext", "m4a")

        lang_up = lang.upper() if lang else "UNK"
        label = f"{_flag(lang)}  {lang_up}  [{ac_s}]  {abr}kbps  {_sz(sz)}"
        audios.append({
            "id":  f.get("format_id", ""),
            "label": label,
            "abr": abr, "sz": sz,
            "lang": lang, "ext": ext,
        })

    audios.sort(key=lambda x: (x["lang"], -x["abr"]))
    seen_a, dedup_a = set(), []
    for a in audios:
        k = (a["lang"], a["ext"])
        if k not in seen_a:
            seen_a.add(k)
            dedup_a.append(a)
    audios = dedup_a[:12]

    # ── SOUS-TITRES ────────────────────────────
    subs = []
    for lang_code, tracks in subtitles.items():
        best = next((t for t in tracks if t.get("ext") in ("vtt","srt")), tracks[0] if tracks else None)
        if not best:
            continue
        subs.append({
            "lang": lang_code,
            "label": f"{_flag(lang_code)}  {lang_code.upper()}  [{best.get('ext','?')}]",
            "url":  best.get("url", ""),
            "ext":  best.get("ext", "srt"),
        })
    subs.sort(key=lambda x: x["lang"])

    session = {
        "url":   url,
        "title": (info.get("title") or "Unknown")[:80],
        "video": videos,
        "audio": audios,
        "subs":  subs,
    }
    _sessions[chat_id] = session
    return session


def get_session(chat_id: int):
    return _sessions.get(chat_id)

def clear_session(chat_id: int):
    _sessions.pop(chat_id, None)


# ─── keyboards ────────────────────────────────

def kb_type(v, a, s) -> InlineKeyboardMarkup:
    """Choix du type de stream."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎬 Vidéo  ({v})",      callback_data="sx_video"),
         InlineKeyboardButton(f"🎵 Audio  ({a})",      callback_data="sx_audio")],
        [InlineKeyboardButton(f"💬 Sous-titres  ({s})",callback_data="sx_subs")],
        [InlineKeyboardButton("⏎ Retour",              callback_data="sx_back")],
    ])

def kb_video(session) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(v["label"], callback_data=f"sx_dl_video_{i}")]
            for i, v in enumerate(session["video"])]
    rows.append([InlineKeyboardButton("⏎ Retour", callback_data="sx_type")])
    return InlineKeyboardMarkup(rows)

def kb_audio(session) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(a["label"], callback_data=f"sx_dl_audio_{i}")]
            for i, a in enumerate(session["audio"])]
    rows.append([InlineKeyboardButton("⏎ Retour", callback_data="sx_type")])
    return InlineKeyboardMarkup(rows)

def kb_subs(session) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(s["label"], callback_data=f"sx_dl_sub_{i}")]
            for i, s in enumerate(session["subs"])]
    rows.append([InlineKeyboardButton("⏎ Retour", callback_data="sx_type")])
    return InlineKeyboardMarkup(rows)


# ─── téléchargement (thread) ──────────────────

def _dl_fmt(url: str, fmt_id: str, out: str):
    opts = {
        "quiet": True, "no_warnings": True,
        "format": fmt_id,
        "outtmpl": f"{out}/%(title)s.%(ext)s",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url)
        return ydl.prepare_filename(info)

def _dl_sub(sub_url: str, out: str, lang: str, ext: str) -> str:
    import urllib.request
    dest = f"{out}/subtitle_{lang}.{ext}"
    urllib.request.urlretrieve(sub_url, dest)
    return dest

async def dl_video(session, idx: int, out: str) -> str:
    v = session["video"][idx]
    return await get_event_loop().run_in_executor(
        _pool, _dl_fmt, session["url"], v["id"], out)

async def dl_audio(session, idx: int, out: str) -> str:
    a = session["audio"][idx]
    return await get_event_loop().run_in_executor(
        _pool, _dl_fmt, session["url"], a["id"], out)

async def dl_sub(session, idx: int, out: str) -> str:
    s = session["subs"][idx]
    return await get_event_loop().run_in_executor(
        _pool, _dl_sub, s["url"], out, s["lang"], s["ext"])
