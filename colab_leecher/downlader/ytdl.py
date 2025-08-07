import logging
import yt_dlp
from asyncio import sleep
from threading import Thread
from os import makedirs, path as ospath
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import YTDL, MSG, Messages, Paths
from colab_leecher.utility.helper import getTime, keyboard, sizeUnit, status_bar, sysINFO


# Format selection presets for different quality options
FORMAT_PRESETS = {
    "best": "best[ext=mp4]/best",
    "worst": "worst[ext=mp4]/worst",
    "720p": "best[height<=720][ext=mp4]/best[height<=720]",
    "480p": "best[height<=480][ext=mp4]/best[height<=480]", 
    "360p": "best[height<=360][ext=mp4]/best[height<=360]",
    "240p": "best[height<=240][ext=mp4]/best[height<=240]",
    "audio_only": "bestaudio[ext=m4a]/bestaudio",
    "video_only": "bestvideo[ext=mp4]/bestvideo"
}


async def YTDL_Status(link, num, quality="best", custom_format=None):
    """
    Enhanced status function with format selection
    
    Args:
        link: YouTube URL
        num: Link number for status display
        quality: Quality preset from FORMAT_PRESETS
        custom_format: Custom yt-dlp format string (overrides quality)
    """
    global Messages, YTDL
    name = await get_YT_Name(link)
    
    quality_display = custom_format if custom_format else quality
    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n"
    Messages.status_head += f"<b>🎯 Quality:</b> <code>{quality_display}</code>\n"
    Messages.status_head += f"<code>{name}</code>\n\n"

    YTDL_Thread = Thread(target=YouTubeDL, name="YouTubeDL", args=(link, quality, custom_format))
    YTDL_Thread.start()

    while YTDL_Thread.is_alive():  # Until ytdl is downloading
        if YTDL.header:
            sys_text = sysINFO()
            message = YTDL.header
            try:
                await MSG.status_msg.edit_text(text=Messages.task_msg + Messages.status_head + message + sys_text, reply_markup=keyboard())
            except Exception:
                pass
        else:
            try:
                await status_bar(
                    down_msg=Messages.status_head,
                    speed=YTDL.speed,
                    percentage=float(YTDL.percentage),
                    eta=YTDL.eta,
                    done=YTDL.done,
                    left=YTDL.left,
                    engine="Xr-YtDL 🏮",
                )
            except Exception:
                pass

        await sleep(2.5)


async def get_available_formats(url):
    """
    Get available formats for a video URL
    
    Returns:
        dict: Available formats with their details
    """
    try:
        with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if "_type" in info and info["_type"] == "playlist":
                # For playlists, get formats from first video
                if info.get("entries"):
                    first_entry = info["entries"][0]
                    info = ydl.extract_info(first_entry["webpage_url"], download=False)
            
            formats = info.get("formats", [])
            available = {}
            
            for fmt in formats:
                if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":  # Video + Audio
                    height = fmt.get("height", 0)
                    fps = fmt.get("fps", 0)
                    ext = fmt.get("ext", "unknown")
                    filesize = fmt.get("filesize") or fmt.get("filesize_approx", 0)
                    
                    quality_key = f"{height}p_{fps}fps" if fps else f"{height}p"
                    available[quality_key] = {
                        "format_id": fmt["format_id"],
                        "height": height,
                        "fps": fps,
                        "ext": ext,
                        "filesize": filesize,
                        "note": fmt.get("format_note", "")
                    }
            
            # Add audio-only formats
            audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get("abr", 0) or 0)
                available["audio_only"] = {
                    "format_id": best_audio["format_id"],
                    "abr": best_audio.get("abr", 0),
                    "ext": best_audio.get("ext", "unknown"),
                    "filesize": best_audio.get("filesize") or best_audio.get("filesize_approx", 0)
                }
            
            return available
    except Exception as e:
        logging.error(f"Error getting formats: {e}")
        return {}


class MyLogger:
    def __init__(self):
        pass

    def debug(self, msg):
        global YTDL
        if "item" in str(msg):
            msgs = msg.split(" ")
            YTDL.header = f"\n⏳ __Getting Video Information {msgs[-3]} of {msgs[-1]}__"

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        # Enhanced error logging for format issues
        if "format" in msg.lower() or "quality" in msg.lower():
            logging.warning(f"Format/Quality issue: {msg}")
        pass


def YouTubeDL(url, quality="best", custom_format=None):
    """
    Enhanced YouTube downloader with format selection
    
    Args:
        url: YouTube URL
        quality: Quality preset key
        custom_format: Custom format string
    """
    global YTDL

    def my_hook(d):
        global YTDL

        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes", 0)
            dl_bytes = d.get("downloaded_bytes", 0)
            percent = d.get("downloaded_percent", 0)
            speed = d.get("speed", "N/A")
            eta = d.get("eta", 0)

            if total_bytes:
                percent = round((float(dl_bytes) * 100 / float(total_bytes)), 2)

            YTDL.header = ""
            YTDL.speed = sizeUnit(speed) if speed != "N/A" and speed else "N/A"
            YTDL.percentage = percent
            YTDL.eta = getTime(eta) if eta else "N/A"
            YTDL.done = sizeUnit(dl_bytes) if dl_bytes else "N/A"
            YTDL.left = sizeUnit(total_bytes) if total_bytes else "N/A"

        elif d["status"] == "downloading fragment":
            pass
        elif d["status"] == "finished":
            YTDL.header = "✅ __Download Completed, Processing...__"
        else:
            logging.info(d)

    # Determine format to use
    if custom_format:
        format_selector = custom_format
    else:
        format_selector = FORMAT_PRESETS.get(quality, FORMAT_PRESETS["best"])

    # Enhanced yt-dlp options with format selection
    ydl_opts = {
        "format": format_selector,
        "allow_multiple_video_streams": True,
        "allow_multiple_audio_streams": True,
        "writethumbnail": True,
        "concurrent_fragments": 4,
        "allow_playlist_files": True,
        "overwrites": True,
        "progress_hooks": [my_hook],
        "logger": MyLogger(),
    }

    # Add post-processors based on quality selection
    if quality == "audio_only":
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }
        ]
    else:
        ydl_opts["postprocessors"] = [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
        ]

    # Add subtitle options if not audio-only
    if quality != "audio_only":
        ydl_opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "srt",
            "subtitleslangs": ["en", "en-US"]
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if not ospath.exists(Paths.thumbnail_ytdl):
            makedirs(Paths.thumbnail_ytdl)
        
        try:
            info_dict = ydl.extract_info(url, download=False)
            YTDL.header = "⌛ __Please WAIT a bit...__"
            
            if "_type" in info_dict and info_dict["_type"] == "playlist":
                playlist_name = info_dict["title"]
                
                # Create quality-specific folder for playlists
                quality_folder = f"{playlist_name}_{quality}" if quality != "best" else playlist_name
                playlist_path = ospath.join(Paths.down_path, quality_folder)
                
                if not ospath.exists(playlist_path):
                    makedirs(playlist_path)
                
                ydl_opts["outtmpl"] = {
                    "default": f"{playlist_path}/%(title)s.%(ext)s",
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                }
                
                # Update ydl with new options
                ydl = yt_dlp.YoutubeDL(ydl_opts)
                
                total_videos = len(info_dict["entries"])
                for i, entry in enumerate(info_dict["entries"], 1):
                    try:
                        YTDL.header = f"📹 __Processing video {i}/{total_videos}__"
                        video_url = entry["webpage_url"]
                        ydl.download([video_url])
                    except yt_dlp.utils.DownloadError as e:
                        logging.error(f"Error downloading video {i}: {e}")
                        # Fallback to basic naming if playlist structure fails
                        if "filename too long" in str(e).lower():
                            ydl_opts["outtmpl"] = {
                                "default": f"{Paths.down_path}/%(id)s.%(ext)s",
                                "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                            }
                            ydl = yt_dlp.YoutubeDL(ydl_opts)
                            ydl.download([video_url])
            else:
                YTDL.header = ""
                # Single video download with quality-aware naming
                if quality != "best":
                    filename_template = f"%(title)s_{quality}.%(ext)s"
                else:
                    filename_template = "%(title)s.%(ext)s"
                
                ydl_opts["outtmpl"] = {
                    "default": f"{Paths.down_path}/{filename_template}",
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                }
                
                ydl = yt_dlp.YoutubeDL(ydl_opts)
                
                try:
                    ydl.download([url])
                except yt_dlp.utils.DownloadError as e:
                    logging.error(f"Download error: {e}")
                    # Fallback to ID-based naming
                    ydl_opts["outtmpl"] = {
                        "default": f"{Paths.down_path}/%(id)s_{quality}.%(ext)s",
                        "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                    }
                    ydl = yt_dlp.YoutubeDL(ydl_opts)
                    ydl.download([url])
                    
        except Exception as e:
            logging.error(f"YTDL ERROR: {e}")
            YTDL.header = f"❌ __Error: {str(e)[:50]}...__"


async def get_YT_Name(link):
    """Enhanced function to get video name with error handling"""
    with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
        try:
            info = ydl.extract_info(link, download=False)
            if "_type" in info and info["_type"] == "playlist":
                title = info.get("title", "UNKNOWN PLAYLIST")
                count = len(info.get("entries", []))
                return f"{title} ({count} videos)"
            elif "title" in info and info["title"]: 
                return info["title"]
            else:
                return "UNKNOWN DOWNLOAD NAME"
        except Exception as e:
            await cancelTask(f"Can't get video info from this link. Because: {str(e)}")
            return "UNKNOWN DOWNLOAD NAME"


# Utility functions for format selection
def get_format_presets():
    """Return available format presets"""
    return list(FORMAT_PRESETS.keys())


async def suggest_quality(url):
    """Suggest optimal quality based on available formats"""
    formats = await get_available_formats(url)
    
    if not formats:
        return "best"
    
    # Prioritize common qualities
    preferred_order = ["720p", "480p", "1080p", "360p", "best"]
    
    for quality in preferred_order:
        matching_formats = [k for k in formats.keys() if quality in k]
        if matching_formats:
            return quality
    
    return "best"


# Example usage functions
async def download_with_quality_selection(url, preferred_qualities=None):
    """
    Download with automatic quality fallback
    
    Args:
        url: YouTube URL
        preferred_qualities: List of preferred qualities in order
    """
    if not preferred_qualities:
        preferred_qualities = ["720p", "480p", "best"]
    
    formats = await get_available_formats(url)
    
    for quality in preferred_qualities:
        if quality in FORMAT_PRESETS:
            try:
                await YTDL_Status(url, 1, quality=quality)
                return
            except Exception as e:
                logging.warning(f"Failed to download with {quality}: {e}")
                continue
    
    # Final fallback
    await YTDL_Status(url, 1, quality="best")
