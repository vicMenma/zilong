import logging
import os
import platform
import psutil
from datetime import datetime
from asyncio import sleep, get_event_loop
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from colab_leecher import colab_bot, OWNER
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import BOT, MSG, BotTimes, Paths
from colab_leecher.utility.task_manager import taskScheduler
from colab_leecher.utility.helper import (
    isLink, setThumbnail, message_deleter, send_settings,
    sizeUnit, getTime, is_ytdl_link, _pct_bar,
)

def _owner_only(m): return m.chat.id == OWNER

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /start
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.delete()
    await message.reply_text(
        "╔━━━━━━━━━━━━━━━━━━━━━━╗\n"
        "║  ⚡  ZILONG  BOT     ║\n"
        "╚━━━━━━━━━━━━━━━━━━━━━━╝\n\n"
        "🟢 <b>Online & Ready</b>\n\n"
        "Send any <b>link</b>, <b>magnet</b> or <b>path</b>.\n"
        "💡 /help for commands",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📣 Support", url="https://t.me/New_Animes_2025"),
        ]])
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /help
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    text = (
        "╔━━━━━━━━━━━━━━━━━━━━━━╗\n"
        "║    📖  HELP CENTER   ║\n"
        "╚━━━━━━━━━━━━━━━━━━━━━━╝\n\n"
        "🔗 <b>Just send a link</b>\n"
        "  HTTP/HTTPS · Magnet · GDrive\n"
        "  Mega · YouTube · Telegram · Path\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️  /settings · /stats · /ping\n"
        "    /cancel · /stop\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎛️ <b>Append to link:</b>\n"
        "  <code>[name.ext]</code>  custom name\n"
        "  <code>{pass}</code>      zip password\n"
        "  <code>(pass)</code>      unzip password\n\n"
        "🖼️  Send an <b>image</b> to set thumbnail"
    )
    msg = await message.reply_text(text)
    await sleep(90)
    await message_deleter(message, msg)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_stats_text():
    def ring(p): return "🟢" if p < 40 else ("🟡" if p < 70 else "🔴")
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net  = psutil.net_io_counters()
    up_s = int((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds())
    return (
        "╔━━━━━━━━━━━━━━━━━━━━━━━╗\n"
        "║   📊  SERVER  STATS   ║\n"
        "╚━━━━━━━━━━━━━━━━━━━━━━━╝\n\n"
        f"🖥  <b>OS</b>     <code>{platform.system()} {platform.release()}</code>\n"
        f"🐍  <b>Python</b> <code>v{platform.python_version()}</code>\n"
        f"⏱  <b>Uptime</b> <code>{getTime(up_s)}</code>\n"
        f"🤖  <b>Task</b>   {'🟠 Running' if BOT.State.task_going else '⚪ Idle'}\n\n"
        f"━━━━  CPU  ━━━━━━━━━━━━━\n"
        f"{ring(cpu)} <code>[{_pct_bar(cpu,15)}]</code> <b>{cpu:.1f}%</b>\n\n"
        f"━━━━  RAM  ━━━━━━━━━━━━━\n"
        f"{ring(ram.percent)} <code>[{_pct_bar(ram.percent,15)}]</code> <b>{ram.percent:.1f}%</b>\n"
        f"   Used <code>{sizeUnit(ram.used)}</code> · Free <code>{sizeUnit(ram.available)}</code>\n\n"
        f"━━━━  DISK  ━━━━━━━━━━━━\n"
        f"{ring(disk.percent)} <code>[{_pct_bar(disk.percent,15)}]</code> <b>{disk.percent:.1f}%</b>\n"
        f"   Used <code>{sizeUnit(disk.used)}</code> · Free <code>{sizeUnit(disk.free)}</code>\n\n"
        f"━━━━  NET  ━━━━━━━━━━━━━\n"
        f"   ⬆️ <code>{sizeUnit(net.bytes_sent)}</code>  ⬇️ <code>{sizeUnit(net.bytes_recv)}</code>\n"
    )

_STATS_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("🔄 Refresh", callback_data="stats_refresh"),
    InlineKeyboardButton("✖ Close",   callback_data="close"),
]])

@colab_bot.on_message(filters.command("stats") & filters.private)
async def stats(client, message):
    if not _owner_only(message): return
    await message.delete()
    await message.reply_text(_build_stats_text(), reply_markup=_STATS_KB)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /ping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    t0  = datetime.now()
    msg = await message.reply_text("⏳")
    ms  = (datetime.now() - t0).microseconds // 1000
    if ms < 100:   q, fill = "🟢 Excellent", 15
    elif ms < 300: q, fill = "🟡 Good",      10
    elif ms < 700: q, fill = "🟠 Fair",       5
    else:          q, fill = "🔴 Poor",        2
    bar = "█" * fill + "░" * (15 - fill)
    await msg.edit_text(
        "╔━━━━━━━━━━━━━━━━━╗\n"
        "║  🏓  P O N G !  ║\n"
        "╚━━━━━━━━━━━━━━━━━╝\n\n"
        f"<code>[{bar}]</code>\n\n"
        f"⚡ <b>Latency</b>  <code>{ms} ms</code>\n"
        f"📶 <b>Quality</b>  {q}\n"
    )
    await sleep(20)
    await message_deleter(message, msg)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Other commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(client, message):
    if not _owner_only(message): return
    await message.delete()
    if BOT.State.task_going:
        await cancelTask("Cancelled via /cancel")
    else:
        msg = await message.reply_text("⚠️ No task running.")
        await sleep(8); await msg.delete()

@colab_bot.on_message(filters.command("stop") & filters.private)
async def stop_bot(client, message):
    if not _owner_only(message): return
    await message.delete()
    if BOT.State.task_going:
        await cancelTask("Bot shutting down")
    await message.reply_text("🛑 <b>Shutting down...</b> 👋")
    await sleep(2)
    await client.stop()
    os._exit(0)

@colab_bot.on_message(filters.command("settings") & filters.private)
async def settings(client, message):
    if _owner_only(message):
        await message.delete()
        await send_settings(client, message, message.id, True)

@colab_bot.on_message(filters.command("setname") & filters.private)
async def custom_name(client, message):
    if len(message.command) != 2:
        msg = await message.reply_text("Usage: <code>/setname filename.ext</code>", quote=True)
    else:
        BOT.Options.custom_name = message.command[1]
        msg = await message.reply_text(f"✅ Name → <code>{BOT.Options.custom_name}</code>", quote=True)
    await sleep(15); await message_deleter(message, msg)

@colab_bot.on_message(filters.command("zipaswd") & filters.private)
async def zip_pswd(client, message):
    if len(message.command) != 2:
        msg = await message.reply_text("Usage: <code>/zipaswd password</code>", quote=True)
    else:
        BOT.Options.zip_pswd = message.command[1]
        msg = await message.reply_text("✅ Zip password set 🔐", quote=True)
    await sleep(15); await message_deleter(message, msg)

@colab_bot.on_message(filters.command("unzipaswd") & filters.private)
async def unzip_pswd(client, message):
    if len(message.command) != 2:
        msg = await message.reply_text("Usage: <code>/unzipaswd password</code>", quote=True)
    else:
        BOT.Options.unzip_pswd = message.command[1]
        msg = await message.reply_text("✅ Unzip password set 🔓", quote=True)
    await sleep(15); await message_deleter(message, msg)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Prefix / Suffix replies
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.reply & filters.private)
async def setPrefix(client, message):
    if BOT.State.prefix:
        BOT.Setting.prefix = message.text; BOT.State.prefix = False
        await send_settings(client, message, message.reply_to_message_id, False)
        await message.delete()
    elif BOT.State.suffix:
        BOT.Setting.suffix = message.text; BOT.State.suffix = False
        await send_settings(client, message, message.reply_to_message_id, False)
        await message.delete()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUTO DOWNLOAD — link stays in chat
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.create(isLink) & ~filters.photo & filters.private)
async def handle_url(client, message):
    if not _owner_only(message): return

    BOT.Options.custom_name = ""
    BOT.Options.zip_pswd    = ""
    BOT.Options.unzip_pswd  = ""

    if BOT.State.task_going:
        msg = await message.reply_text("⚠️ Task running — /cancel first.", quote=True)
        await sleep(8); await msg.delete()
        return

    temp_source = message.text.splitlines()
    for _ in range(3):
        if not temp_source: break
        last = temp_source[-1].strip()
        if   last.startswith("[") and last.endswith("]"): BOT.Options.custom_name = last[1:-1]; temp_source.pop()
        elif last.startswith("{") and last.endswith("}"): BOT.Options.zip_pswd    = last[1:-1]; temp_source.pop()
        elif last.startswith("(") and last.endswith(")"): BOT.Options.unzip_pswd  = last[1:-1]; temp_source.pop()
        else: break

    BOT.SOURCE    = temp_source
    BOT.Mode.ytdl = all(is_ytdl_link(l) for l in temp_source if l.strip())
    BOT.Mode.mode = "leech"
    BOT.State.started = True

    n     = len([l for l in temp_source if l.strip()])
    label = "🏮 YTDL" if BOT.Mode.ytdl else "🔗 Link"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Regular",     callback_data="normal"),
         InlineKeyboardButton("🗜️ Compress",    callback_data="zip")],
        [InlineKeyboardButton("📂 Extract",     callback_data="unzip"),
         InlineKeyboardButton("♻️ UnDoubleZip", callback_data="undzip")],
    ])
    await message.reply_text(
        f"  {label} · <code>{n}</code> source(s)\n  <b>Choose mode:</b>",
        reply_markup=kb, quote=True,
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Callbacks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_callback_query()
async def handle_options(client, callback_query):
    data = callback_query.data

    if data == "stats_refresh":
        try: await callback_query.message.edit_text(_build_stats_text(), reply_markup=_STATS_KB)
        except Exception: pass
        return

    if data in ["normal", "zip", "unzip", "undzip"]:
        BOT.Mode.type = data
        await callback_query.message.delete()   # remove mode picker only
        MSG.status_msg = await colab_bot.send_message(
            chat_id=OWNER,
            text="⏳ <i>Starting...</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]]),
        )
        BOT.State.task_going = True
        BOT.State.started    = False
        BotTimes.start_time  = datetime.now()
        BOT.TASK = get_event_loop().create_task(taskScheduler())
        await BOT.TASK
        BOT.State.task_going = False
        return

    if data == "video":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✂️ Split",     callback_data="split-true"),
             InlineKeyboardButton("🗜️ Zip",       callback_data="split-false")],
            [InlineKeyboardButton("🔄 Convert",   callback_data="convert-true"),
             InlineKeyboardButton("🚫 Skip",      callback_data="convert-false")],
            [InlineKeyboardButton("🎬 MP4",       callback_data="mp4"),
             InlineKeyboardButton("📦 MKV",       callback_data="mkv")],
            [InlineKeyboardButton("🔝 High",      callback_data="q-High"),
             InlineKeyboardButton("📉 Low",       callback_data="q-Low")],
            [InlineKeyboardButton("⏎ Back",       callback_data="back")],
        ])
        await callback_query.message.edit_text(
            "╔━━━━━━━━━━━━━━━━━━━━━╗\n"
            "║  🎥  VIDEO SETTINGS  ║\n"
            "╚━━━━━━━━━━━━━━━━━━━━━╝\n\n"
            f"  Convert  <code>{BOT.Setting.convert_video}</code>\n"
            f"  Split    <code>{BOT.Setting.split_video}</code>\n"
            f"  Format   <code>{BOT.Options.video_out.upper()}</code>\n"
            f"  Quality  <code>{BOT.Setting.convert_quality}</code>",
            reply_markup=kb)
    elif data == "caption":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Monospace", callback_data="code-Monospace"),
             InlineKeyboardButton("Bold",      callback_data="b-Bold")],
            [InlineKeyboardButton("Italic",    callback_data="i-Italic"),
             InlineKeyboardButton("Underline", callback_data="u-Underlined")],
            [InlineKeyboardButton("Regular",   callback_data="p-Regular")],
            [InlineKeyboardButton("⏎ Back",    callback_data="back")],
        ])
        await callback_query.message.edit_text(
            f"✏️ <b>Caption Style</b>  current: <code>{BOT.Setting.caption}</code>",
            reply_markup=kb)
    elif data == "thumb":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete", callback_data="del-thumb")],
            [InlineKeyboardButton("⏎ Back",    callback_data="back")],
        ])
        await callback_query.message.edit_text(
            f"🖼️ <b>Thumbnail</b>  {'✅ Set' if BOT.Setting.thumbnail else '❌ None'}\n"
            "Send an image to update.", reply_markup=kb)
    elif data == "del-thumb":
        if BOT.Setting.thumbnail:
            try: os.remove(Paths.THMB_PATH)
            except Exception: pass
        BOT.Setting.thumbnail = False
        await send_settings(client, callback_query.message, callback_query.message.id, False)
    elif data == "set-prefix":
        await callback_query.message.edit_text("Reply with your <b>prefix</b> text:")
        BOT.State.prefix = True
    elif data == "set-suffix":
        await callback_query.message.edit_text("Reply with your <b>suffix</b> text:")
        BOT.State.suffix = True
    elif data in ["code-Monospace","p-Regular","b-Bold","i-Italic","u-Underlined"]:
        r = data.split("-"); BOT.Options.caption = r[0]; BOT.Setting.caption = r[1]
        await send_settings(client, callback_query.message, callback_query.message.id, False)
    elif data in ["split-true","split-false"]:
        BOT.Options.is_split = data == "split-true"
        BOT.Setting.split_video = "Split Videos" if data == "split-true" else "Zip Videos"
        await send_settings(client, callback_query.message, callback_query.message.id, False)
    elif data in ["convert-true","convert-false","mp4","mkv","q-High","q-Low"]:
        if data in ["convert-true","convert-false"]:
            BOT.Options.convert_video = data == "convert-true"
            BOT.Setting.convert_video = "Yes" if data == "convert-true" else "No"
        elif data in ["q-High","q-Low"]:
            BOT.Setting.convert_quality = data.split("-")[-1]
            BOT.Options.convert_quality = BOT.Setting.convert_quality == "High"
        else:
            BOT.Options.video_out = data
        await send_settings(client, callback_query.message, callback_query.message.id, False)
    elif data in ["media","document"]:
        BOT.Options.stream_upload = data == "media"
        BOT.Setting.stream_upload = "Media" if data == "media" else "Document"
        await send_settings(client, callback_query.message, callback_query.message.id, False)
    elif data == "close":
        await callback_query.message.delete()
    elif data == "back":
        await send_settings(client, callback_query.message, callback_query.message.id, False)
    elif data == "cancel":
        await cancelTask("User cancelled")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Photo → thumbnail
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@colab_bot.on_message(filters.photo & filters.private)
async def handle_image(client, message):
    msg = await message.reply_text("⏳ <i>Saving thumbnail...</i>")
    if await setThumbnail(message):
        await msg.edit_text("✅ Thumbnail updated.")
        await message.delete()
    else:
        await msg.edit_text("❌ Could not set thumbnail.")
    await sleep(10)
    await message_deleter(message, msg)

logging.info("⚡ Zilong started.")
colab_bot.run()
