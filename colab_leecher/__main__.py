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
    isLink,
    setThumbnail,
    message_deleter,
    send_settings,
    sizeUnit,
    getTime,
)

# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _owner_only(message):
    return message.chat.id == OWNER


# ──────────────────────────────────────────────
#  /start
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.delete()
    text = (
        "**Hey There** I'm Online 🚀 Ready to operate\n\n"
        "Just send me any **link / magnet / torrent** and I'll handle it automatically!\n\n"
        "Use /help to see all commands."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Support 💝", url="https://t.me/New_Animes_2025"),
    ]])
    await message.reply_text(text, reply_markup=keyboard)


# ──────────────────────────────────────────────
#  /help
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    text = (
        "**📖 How to use me:**\n\n"
        "Just **send a link / magnet / torrent** directly — no command needed!\n"
        "I'll detect what it is and ask you how to process it.\n\n"
        "**⚙️ Commands:**\n"
        "`/settings` — Edit bot settings\n"
        "`/setname <name>` — Set a custom file name 📛\n"
        "`/zipaswd <pass>` — Password for output zip 🔐\n"
        "`/unzipaswd <pass>` — Password for extracting archives 🔓\n"
        "`/stats` — Show server resource usage 📊\n"
        "`/ping` — Check bot response time 🏓\n"
        "`/cancel` — Cancel the running task ❌\n"
        "`/stop` — Shut down the bot 🛑\n\n"
        "⚠️ You can **send an image** at any time to set it as thumbnail 🌄"
    )
    msg = await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Instructions 📖",
                url="https://github.com/XronTrix10/Telegram-Leecher/wiki/INSTRUCTIONS",
            )
        ]]),
    )
    await sleep(60)
    await message_deleter(message, msg)


# ──────────────────────────────────────────────
#  /stats — server resource monitor
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("stats") & filters.private)
async def stats(client, message):
    if not _owner_only(message):
        return
    await message.delete()

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_secs = (datetime.now() - boot_time).seconds
    net = psutil.net_io_counters()
    python_ver = platform.python_version()
    os_info = f"{platform.system()} {platform.release()}"

    text = (
        "**📊 Server Stats**\n\n"
        f"🖥️ **OS:** `{os_info}`\n"
        f"🐍 **Python:** `{python_ver}`\n\n"
        f"⚡ **CPU Usage:** `{cpu}%`\n\n"
        f"💽 **RAM:**\n"
        f"  ├ Total: `{sizeUnit(ram.total)}`\n"
        f"  ├ Used:  `{sizeUnit(ram.used)}` ({ram.percent}%)\n"
        f"  ╰ Free:  `{sizeUnit(ram.available)}`\n\n"
        f"💾 **Disk:**\n"
        f"  ├ Total: `{sizeUnit(disk.total)}`\n"
        f"  ├ Used:  `{sizeUnit(disk.used)}` ({disk.percent}%)\n"
        f"  ╰ Free:  `{sizeUnit(disk.free)}`\n\n"
        f"🌐 **Network:**\n"
        f"  ├ Sent:     `{sizeUnit(net.bytes_sent)}`\n"
        f"  ╰ Received: `{sizeUnit(net.bytes_recv)}`\n\n"
        f"⏱️ **Uptime:** `{getTime(uptime_secs)}`"
    )
    msg = await message.reply_text(text)
    await sleep(60)
    try:
        await msg.delete()
    except Exception:
        pass


# ──────────────────────────────────────────────
#  /ping
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    start_t = datetime.now()
    msg = await message.reply_text("🏓 Pong!")
    end_t = datetime.now()
    latency_ms = (end_t - start_t).microseconds // 1000
    await msg.edit_text(f"🏓 **Pong!**\n⚡ Latency: `{latency_ms} ms`")
    await sleep(15)
    await message_deleter(message, msg)


# ──────────────────────────────────────────────
#  /cancel — cancel running task
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(client, message):
    if not _owner_only(message):
        return
    await message.delete()
    if BOT.State.task_going:
        await cancelTask("Cancelled via /cancel command")
    else:
        msg = await message.reply_text("⚠️ No task is currently running.")
        await sleep(10)
        await msg.delete()


# ──────────────────────────────────────────────
#  /stop — shut down bot
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("stop") & filters.private)
async def stop_bot(client, message):
    if not _owner_only(message):
        return
    await message.delete()
    if BOT.State.task_going:
        await cancelTask("Bot is shutting down")
    await message.reply_text("🛑 **Bot is shutting down...**\nBye! 👋")
    await sleep(2)
    await client.stop()
    os._exit(0)


# ──────────────────────────────────────────────
#  /settings
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("settings") & filters.private)
async def settings(client, message):
    if _owner_only(message):
        await message.delete()
        await send_settings(client, message, message.id, True)


# ──────────────────────────────────────────────
#  /setname  /zipaswd  /unzipaswd
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.command("setname") & filters.private)
async def custom_name(client, message):
    if len(message.command) != 2:
        msg = await message.reply_text(
            "Send\n/setname <code>custom_filename.extension</code>\nTo Set Custom File Name 📛",
            quote=True,
        )
    else:
        BOT.Options.custom_name = message.command[1]
        msg = await message.reply_text("Custom Name Has Been Successfully Set ✅", quote=True)
    await sleep(15)
    await message_deleter(message, msg)


@colab_bot.on_message(filters.command("zipaswd") & filters.private)
async def zip_pswd(client, message):
    if len(message.command) != 2:
        msg = await message.reply_text(
            "Send\n/zipaswd <code>password</code>\nTo Set Password for Output Zip File 🔐",
            quote=True,
        )
    else:
        BOT.Options.zip_pswd = message.command[1]
        msg = await message.reply_text("Zip Password Has Been Successfully Set ✅", quote=True)
    await sleep(15)
    await message_deleter(message, msg)


@colab_bot.on_message(filters.command("unzipaswd") & filters.private)
async def unzip_pswd(client, message):
    if len(message.command) != 2:
        msg = await message.reply_text(
            "Send\n/unzipaswd <code>password</code>\nTo Set Password for Extracting Archives 🔓",
            quote=True,
        )
    else:
        BOT.Options.unzip_pswd = message.command[1]
        msg = await message.reply_text("Unzip Password Has Been Successfully Set ✅", quote=True)
    await sleep(15)
    await message_deleter(message, msg)


# ──────────────────────────────────────────────
#  Prefix / Suffix replies
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.reply)
async def setPrefix(client, message):
    if BOT.State.prefix:
        BOT.Setting.prefix = message.text
        BOT.State.prefix = False
        await send_settings(client, message, message.reply_to_message_id, False)
        await message.delete()
    elif BOT.State.suffix:
        BOT.Setting.suffix = message.text
        BOT.State.suffix = False
        await send_settings(client, message, message.reply_to_message_id, False)
        await message.delete()


# ──────────────────────────────────────────────
#  AUTO DOWNLOAD — triggered by any link/magnet
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.create(isLink) & ~filters.photo & filters.private)
async def handle_url(client, message):
    """
    Automatically handle any link/magnet/path sent by the owner.
    No /tupload or /ytupload needed — the bot figures it out.
    """
    if not _owner_only(message):
        return

    # Reset per-task options
    BOT.Options.custom_name = ""
    BOT.Options.zip_pswd = ""
    BOT.Options.unzip_pswd = ""

    # If a task is already running, tell the user
    if BOT.State.task_going:
        await message.reply_text(
            "⚠️ **A task is already running!**\nUse /cancel to stop it first.",
            quote=True,
        )
        return

    # Parse the message — last lines starting with [ { ( are options
    temp_source = message.text.splitlines()
    for _ in range(3):
        if not temp_source:
            break
        last = temp_source[-1].strip()
        if last.startswith("[") and last.endswith("]"):
            BOT.Options.custom_name = last[1:-1]
            temp_source.pop()
        elif last.startswith("{") and last.endswith("}"):
            BOT.Options.zip_pswd = last[1:-1]
            temp_source.pop()
        elif last.startswith("(") and last.endswith(")"):
            BOT.Options.unzip_pswd = last[1:-1]
            temp_source.pop()
        else:
            break

    BOT.SOURCE = temp_source

    # Auto-detect ytdl links so we can pre-select the toggle
    from colab_leecher.utility.helper import is_ytdl_link
    all_ytdl = all(is_ytdl_link(l) for l in temp_source if l.strip())
    BOT.Mode.ytdl = all_ytdl
    BOT.Mode.mode = "leech"

    # Mark bot as "started" (waiting for type selection)
    BOT.State.started = True

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Regular", callback_data="normal")],
        [
            InlineKeyboardButton("Compress 🗜️", callback_data="zip"),
            InlineKeyboardButton("Extract 📂", callback_data="unzip"),
        ],
        [InlineKeyboardButton("UnDoubleZip ♻️", callback_data="undzip")],
    ])

    mode_label = "YouTube/YTDL" if all_ytdl else "Leech"
    await message.reply_text(
        text=(
            f"<b>🐹 Auto-detected: {mode_label} »</b>\n\n"
            "Regular: <i>Normal file upload</i>\n"
            "Compress: <i>Zip before upload</i>\n"
            "Extract: <i>Extract before upload</i>\n"
            "UnDoubleZip: <i>Unzip then re-compress</i>"
        ),
        reply_markup=keyboard,
        quote=True,
    )


# ──────────────────────────────────────────────
#  Callback query handler
# ──────────────────────────────────────────────

@colab_bot.on_callback_query()
async def handle_options(client, callback_query):
    data = callback_query.data

    # ── Task type selection ──────────────────
    if data in ["normal", "zip", "unzip", "undzip"]:
        BOT.Mode.type = data
        await callback_query.message.delete()
        try:
            await colab_bot.delete_messages(
                chat_id=callback_query.message.chat.id,
                message_ids=callback_query.message.reply_to_message_id,
            )
        except Exception:
            pass

        MSG.status_msg = await colab_bot.send_message(
            chat_id=OWNER,
            text="#STARTING_TASK\n\n**Starting your task in a few seconds... 🦐**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Cancel ❌", callback_data="cancel")
            ]]),
        )
        BOT.State.task_going = True
        BOT.State.started = False
        BotTimes.start_time = datetime.now()
        event_loop = get_event_loop()
        BOT.TASK = event_loop.create_task(taskScheduler())
        await BOT.TASK
        BOT.State.task_going = False

    # ── Settings sub-menus ───────────────────
    elif data == "video":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Split Videos", callback_data="split-true"),
                InlineKeyboardButton("Zip Videos", callback_data="split-false"),
            ],
            [
                InlineKeyboardButton("Convert", callback_data="convert-true"),
                InlineKeyboardButton("Don't Convert", callback_data="convert-false"),
            ],
            [
                InlineKeyboardButton("To » Mp4", callback_data="mp4"),
                InlineKeyboardButton("To » Mkv", callback_data="mkv"),
            ],
            [
                InlineKeyboardButton("High Quality", callback_data="q-High"),
                InlineKeyboardButton("Low Quality", callback_data="q-Low"),
            ],
            [InlineKeyboardButton("Back ⏎", callback_data="back")],
        ])
        await callback_query.message.edit_text(
            f"CHOOSE YOUR DESIRED OPTION ⚙️ »\n\n"
            f"╭⌬ CONVERT » <code>{BOT.Setting.convert_video}</code>\n"
            f"├⌬ SPLIT » <code>{BOT.Setting.split_video}</code>\n"
            f"├⌬ OUTPUT FORMAT » <code>{BOT.Options.video_out}</code>\n"
            f"╰⌬ OUTPUT QUALITY » <code>{BOT.Setting.convert_quality}</code>",
            reply_markup=keyboard,
        )

    elif data == "caption":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Monospace", callback_data="code-Monospace"),
                InlineKeyboardButton("Bold", callback_data="b-Bold"),
            ],
            [
                InlineKeyboardButton("Italic", callback_data="i-Italic"),
                InlineKeyboardButton("Underlined", callback_data="u-Underlined"),
            ],
            [InlineKeyboardButton("Regular", callback_data="p-Regular")],
        ])
        await callback_query.message.edit_text(
            "CHOOSE YOUR CAPTION FONT STYLE »\n\n"
            "⌬ <code>Monospace</code>\n⌬ Regular\n⌬ <b>Bold</b>\n⌬ <i>Italic</i>\n⌬ <u>Underlined</u>",
            reply_markup=keyboard,
        )

    elif data == "thumb":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Delete Thumbnail", callback_data="del-thumb")],
            [InlineKeyboardButton("Go Back ⏎", callback_data="back")],
        ])
        thmb_ = "None" if not BOT.Setting.thumbnail else "Exists"
        await callback_query.message.edit_text(
            f"CHOOSE YOUR THUMBNAIL SETTINGS »\n\n"
            f"⌬ Thumbnail » {thmb_}\n"
            f"⌬ Send an Image to set as Your Thumbnail",
            reply_markup=keyboard,
        )

    elif data == "del-thumb":
        if BOT.Setting.thumbnail:
            import os as _os
            _os.remove(Paths.THMB_PATH)
        BOT.Setting.thumbnail = False
        await send_settings(client, callback_query.message, callback_query.message.id, False)

    elif data == "set-prefix":
        await callback_query.message.edit_text(
            "Send a Text to Set as PREFIX by REPLYING THIS MESSAGE »"
        )
        BOT.State.prefix = True

    elif data == "set-suffix":
        await callback_query.message.edit_text(
            "Send a Text to Set as SUFFIX by REPLYING THIS MESSAGE »"
        )
        BOT.State.suffix = True

    elif data in ["code-Monospace", "p-Regular", "b-Bold", "i-Italic", "u-Underlined"]:
        res = data.split("-")
        BOT.Options.caption = res[0]
        BOT.Setting.caption = res[1]
        await send_settings(client, callback_query.message, callback_query.message.id, False)

    elif data in ["split-true", "split-false"]:
        BOT.Options.is_split = data == "split-true"
        BOT.Setting.split_video = "Split Videos" if data == "split-true" else "Zip Videos"
        await send_settings(client, callback_query.message, callback_query.message.id, False)

    elif data in ["convert-true", "convert-false", "mp4", "mkv", "q-High", "q-Low"]:
        if data in ["convert-true", "convert-false"]:
            BOT.Options.convert_video = data == "convert-true"
            BOT.Setting.convert_video = "Yes" if data == "convert-true" else "No"
        elif data in ["q-High", "q-Low"]:
            BOT.Setting.convert_quality = data.split("-")[-1]
            BOT.Options.convert_quality = BOT.Setting.convert_quality == "High"
        else:
            BOT.Options.video_out = data
        await send_settings(client, callback_query.message, callback_query.message.id, False)

    elif data in ["media", "document"]:
        BOT.Options.stream_upload = data == "media"
        BOT.Setting.stream_upload = "Media" if data == "media" else "Document"
        await send_settings(client, callback_query.message, callback_query.message.id, False)

    elif data == "close":
        await callback_query.message.delete()

    elif data == "back":
        await send_settings(client, callback_query.message, callback_query.message.id, False)

    elif data == "cancel":
        await cancelTask("User Cancelled !")


# ──────────────────────────────────────────────
#  Photo → thumbnail
# ──────────────────────────────────────────────

@colab_bot.on_message(filters.photo & filters.private)
async def handle_image(client, message):
    msg = await message.reply_text("<i>Trying To Save Thumbnail...</i>")
    success = await setThumbnail(message)
    if success:
        await msg.edit_text("**Thumbnail Successfully Changed ✅**")
        await message.delete()
    else:
        await msg.edit_text("🥲 **Couldn't Set Thumbnail, Please Try Again!**", quote=True)
    await sleep(15)
    await message_deleter(message, msg)


# ──────────────────────────────────────────────
#  Boot
# ──────────────────────────────────────────────

logging.info("Zilong Started! Send any link to begin downloading.")
colab_bot.run()
