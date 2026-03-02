"""
stream_extractor.py
─────────────────────────────────────────────────
Analyse un URL/fichier et liste toutes les pistes :
  - yt-dlp  : YouTube, Twitch, etc. (plateformes streaming)
  - ffprobe : TOUT le reste (liens directs, seedr, DDL, fichiers locaux)
  Les deux sont tentés, ffprobe gagne sur les liens directs.
"""
import json
import logging
import subprocess
import yt_dlp
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_sessions: dict = {}
_pool = ThreadPoolExecutor(max_workers=2)


# ─── formatage ────────────────────────────────

def _sz(b) -> str:
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
    "vi":"🇻🇳","id":"🇮🇩","ms":"🇲🇾","no":"🇳🇴","und":"🌐",
}

def _flag(code: str) -> str:
    if not code:
        return "🌐"
    return _FLAGS.get(code.split("-")[0].lower()[:3], "🌐")


# ─── ffprobe (liens directs, fichiers locaux) ─

def _ffprobe_sync(url: str) -> dict | None:
    """
    Appelle ffprobe sur l'URL et retourne les infos JSON.
    Fonctionne sur n'importe quel fichier/lien HTTP direct.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except Exception as e:
        logging.warning(f"[ffprobe] error: {e}")
        return None


def _parse_ffprobe(info: dict, url: str) -> dict:
    """Convertit la sortie ffprobe en session standardisée."""
    streams   = info.get("streams", [])
    fmt       = info.get("format", {})
    duration  = float(fmt.get("duration") or 0)
    total_sz  = int(fmt.get("size") or 0)
    title     = fmt.get("tags", {}).get("title") or url.split("/")[-1][:80]

    videos, audios, subs = [], [], []

    for s in streams:
        codec_type = s.get("codec_type", "")
        codec_name = s.get("codec_name", "unknown")
        lang       = (s.get("tags") or {}).get("language", "")
        idx        = s.get("index", 0)
        title_tag  = (s.get("tags") or {}).get("title", "")

        if codec_type == "video":
            w   = s.get("width") or 0
            h   = s.get("height") or 0
            fps_raw = s.get("r_frame_rate", "0/1")
            try:
                num, den = fps_raw.split("/")
                fps = round(int(num) / int(den))
            except Exception:
                fps = 0
            # taille estimée par durée × bitrate
            br  = int(s.get("bit_rate") or 0)
            sz  = int(br * duration / 8) if br and duration else 0

            res = f"{h}p" if h else f"{w}×{h}"
            if fps > 30:
                res += f" {fps}fps"
            label = f"🎬  {res}  [{codec_name}]  {_sz(sz or total_sz)}"
            if title_tag:
                label += f"  {title_tag}"

            videos.append({
                "id": str(idx), "label": label,
                "h": h, "fps": fps, "sz": sz,
                "lang": lang, "codec": codec_name,
                "map": f"0:{idx}",
                "ext": "mkv",
            })

        elif codec_type == "audio":
            channels = s.get("channels") or 0
            sample   = s.get("sample_rate") or ""
            br       = int(s.get("bit_rate") or 0)
            sz       = int(br * duration / 8) if br and duration else 0
            lang_up  = lang.upper() if lang else "UNK"

            ch_str = f"{channels}ch" if channels else ""
            br_str = f"{br//1000}kbps" if br else ""
            label  = f"{_flag(lang)}  {lang_up}  [{codec_name}]  {ch_str}  {br_str}  {_sz(sz)}"
            if title_tag:
                label += f"  {title_tag}"

            audios.append({
                "id": str(idx), "label": label.strip(),
                "abr": br // 1000 if br else 0,
                "sz": sz, "lang": lang,
                "map": f"0:{idx}",
                "ext": "mka",
            })

        elif codec_type == "subtitle":
            lang_up = lang.upper() if lang else "UNK"
            label   = f"{_flag(lang)}  {lang_up}  [{codec_name}]"
            if title_tag:
                label += f"  {title_tag}"

            subs.append({
                "id": str(idx), "label": label,
                "lang": lang,
                "map": f"0:{idx}",
                "ext": "srt" if codec_name in ("subrip","mov_text") else "ass",
                "url": None,   # extraction locale
            })

    return {
        "url":    url,
        "title":  title,
        "video":  videos,
        "audio":  audios,
        "subs":   subs,
        "source": "ffprobe",
    }


# ─── yt-dlp (plateformes streaming) ──────────

def _ytdlp_sync(url: str) -> dict | None:
    opts = {
        "quiet": True, "no_warnings": True,
        "skip_download": True, "noplaylist": True,
        "ignoreerrors": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        if not info.get("formats"):
            return None
        return info
    except Exception as e:
        logging.debug(f"[yt-dlp] {e}")
        return None


def _parse_ytdlp(info: dict, url: str) -> dict:
    formats   = info.get("formats") or []
    subtitles = info.get("subtitles") or {}

    videos, audios, subs = [], [], []

    for f in formats:
        vc = f.get("vcodec", "none")
        ac = f.get("acodec", "none")
        if vc == "none":
            continue
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
            "id": f.get("format_id", ""), "label": label,
            "h": h, "fps": fps, "sz": sz,
            "lang": lang, "ext": f.get("ext", "mp4"),
            "has_audio": ac != "none",
        })

    videos.sort(key=lambda x: (x["h"], x["fps"]), reverse=True)
    seen_v, dedup_v = set(), []
    for v in videos:
        k = (v["h"], v.get("has_audio", True))
        if k not in seen_v:
            seen_v.add(k); dedup_v.append(v)
    videos = dedup_v[:12]

    for f in formats:
        vc = f.get("vcodec", "none")
        ac = f.get("acodec", "none")
        if vc != "none" or ac == "none":
            continue
        abr  = int(f.get("abr") or f.get("tbr") or 0)
        sz   = f.get("filesize") or f.get("filesize_approx") or 0
        lang = f.get("language") or ""
        ac_s = ac.split(".")[0]
        ext  = f.get("ext", "m4a")
        lang_up = lang.upper() if lang else "UNK"
        label = f"{_flag(lang)}  {lang_up}  [{ac_s}]  {abr}kbps  {_sz(sz)}"
        audios.append({
            "id": f.get("format_id",""), "label": label,
            "abr": abr, "sz": sz, "lang": lang, "ext": ext,
        })

    audios.sort(key=lambda x: (x["lang"], -x["abr"]))
    seen_a, dedup_a = set(), []
    for a in audios:
        k = (a["lang"], a["ext"])
        if k not in seen_a:
            seen_a.add(k); dedup_a.append(a)
    audios = dedup_a[:12]

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

    return {
        "url":    url,
        "title":  (info.get("title") or "Unknown")[:80],
        "video":  videos,
        "audio":  audios,
        "subs":   subs,
        "source": "ytdlp",
    }


# ─── point d'entrée principal ─────────────────

async def analyse(url: str, chat_id: int) -> dict | None:
    """
    Essaie d'abord ffprobe (rapide, universel),
    puis yt-dlp si ffprobe ne trouve rien.
    """
    loop = get_event_loop()

    # 1. ffprobe — fonctionne sur tout lien HTTP direct
    raw = await loop.run_in_executor(_pool, _ffprobe_sync, url)
    if raw and raw.get("streams"):
        session = _parse_ffprobe(raw, url)
        if session["video"] or session["audio"] or session["subs"]:
            _sessions[chat_id] = session
            return session

    # 2. yt-dlp — plateformes streaming
    info = await loop.run_in_executor(_pool, _ytdlp_sync, url)
    if info:
        session = _parse_ytdlp(info, url)
        if session["video"] or session["audio"] or session["subs"]:
            _sessions[chat_id] = session
            return session

    return None


def get_session(chat_id: int):
    return _sessions.get(chat_id)

def clear_session(chat_id: int):
    _sessions.pop(chat_id, None)


# ─── keyboards ────────────────────────────────

def kb_type(v, a, s) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎬 Vidéo  ({v})",       callback_data="sx_video"),
         InlineKeyboardButton(f"🎵 Audio  ({a})",       callback_data="sx_audio")],
        [InlineKeyboardButton(f"💬 Sous-titres  ({s})", callback_data="sx_subs")],
        [InlineKeyboardButton("⏎ Retour",               callback_data="sx_back")],
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


# ─── téléchargement ───────────────────────────

def _dl_ytdlp(url: str, fmt_id: str, out: str) -> str:
    opts = {
        "quiet": True, "no_warnings": True,
        "format": fmt_id,
        "outtmpl": f"{out}/%(title)s.%(ext)s",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url)
        return ydl.prepare_filename(info)


def _dl_ffmpeg(url: str, stream_map: str, out_file: str) -> str:
    """Extrait une piste précise avec ffmpeg (map 0:N)."""
    cmd = [
        "ffmpeg", "-y", "-i", url,
        "-map", stream_map,
        "-c", "copy",
        out_file,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode()[-300:])
    return out_file


def _dl_sub_url(sub_url: str, out: str, lang: str, ext: str) -> str:
    import urllib.request
    dest = f"{out}/subtitle_{lang}.{ext}"
    urllib.request.urlretrieve(sub_url, dest)
    return dest


async def dl_video(session, idx: int, out: str) -> str:
    v    = session["video"][idx]
    loop = get_event_loop()
    if session["source"] == "ytdlp":
        return await loop.run_in_executor(_pool, _dl_ytdlp, session["url"], v["id"], out)
    else:
        fname = f"{out}/video_stream_{idx}.{v['ext']}"
        return await loop.run_in_executor(_pool, _dl_ffmpeg, session["url"], v["map"], fname)


async def dl_audio(session, idx: int, out: str) -> str:
    a    = session["audio"][idx]
    loop = get_event_loop()
    if session["source"] == "ytdlp":
        return await loop.run_in_executor(_pool, _dl_ytdlp, session["url"], a["id"], out)
    else:
        fname = f"{out}/audio_stream_{idx}.{a['ext']}"
        return await loop.run_in_executor(_pool, _dl_ffmpeg, session["url"], a["map"], fname)


async def dl_sub(session, idx: int, out: str) -> str:
    s    = session["subs"][idx]
    loop = get_event_loop()
    if s.get("url"):
        return await loop.run_in_executor(_pool, _dl_sub_url, s["url"], out, s["lang"], s["ext"])
    else:
        fname = f"{out}/subtitle_{s['lang']}_{idx}.{s['ext']}"
        return await loop.run_in_executor(_pool, _dl_ffmpeg, session["url"], s["map"], fname)
