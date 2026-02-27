import os
import shutil
import logging
import pathlib
from asyncio import sleep
from time import time
from colab_leecher import OWNER, colab_bot
from natsort import natsorted
from datetime import datetime
from os import makedirs, path as ospath
from colab_leecher.uploader.telegram import upload_file
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from colab_leecher.utility.variables import (
    BOT, MSG, BotTimes, Messages, Paths, Transfer,
)
from colab_leecher.utility.converters import (
    archive, extract, videoConverter, sizeChecker,
)
from colab_leecher.utility.helper import (
    fileType, getSize, getTime, keyboard,
    shortFileName, sizeUnit, sysINFO, _pct_bar,
)


async def Leech(folder_path: str, remove: bool):
    # Convert videos if needed
    files = [str(p) for p in pathlib.Path(folder_path).glob("**/*") if p.is_file()]
    for f in natsorted(files):
        fp = ospath.join(folder_path, f)
        if BOT.Options.convert_video and fileType(fp) == "video":
            await videoConverter(fp)

    Transfer.total_down_size = getSize(folder_path)

    # Collect all files to upload so we know which is last
    files = natsorted([str(p) for p in pathlib.Path(folder_path).glob("**/*") if p.is_file()])
    upload_queue = []  # list of (file_path, will_be_split)

    for f in files:
        file_path = ospath.join(folder_path, f)
        leech = await sizeChecker(file_path, remove)
        if leech:
            if ospath.exists(file_path) and remove:
                os.remove(file_path)
            parts = natsorted(os.listdir(Paths.temp_zpath))
            for part in parts:
                upload_queue.append(("split", ospath.join(Paths.temp_zpath, part)))
        else:
            upload_queue.append(("single", file_path))

    total_uploads = len(upload_queue)

    split_cleanup_done = False

    for idx, (kind, file_path) in enumerate(upload_queue):
        is_last = (idx == total_uploads - 1)

        if kind == "split":
            file_name = ospath.basename(file_path)
            new_path  = shortFileName(file_path)
            os.rename(file_path, new_path)
            BotTimes.current_time = time()
            Messages.status_head  = (
                f"<b>📤 UPLOADING</b>  "
                f"<i>{idx + 1}/{total_uploads}</i>\n\n"
                f"<code>{file_name}</code>\n"
            )
            try:
                MSG.status_msg = await MSG.status_msg.edit_text(
                    text=Messages.task_msg + Messages.status_head
                    + "\n⏳ <i>Starting...</i>" + sysINFO(),
                    reply_markup=keyboard(),
                )
            except Exception: pass
            await upload_file(new_path, file_name, is_last=is_last)
            Transfer.up_bytes.append(os.stat(new_path).st_size)

            # Clean temp split folder after last split part
            if is_last and not split_cleanup_done:
                if ospath.exists(Paths.temp_zpath):
                    shutil.rmtree(Paths.temp_zpath)
                split_cleanup_done = True

        else:  # single
            if not ospath.exists(Paths.temp_files_dir):
                makedirs(Paths.temp_files_dir)
            if not remove:
                file_path = shutil.copy(file_path, Paths.temp_files_dir)

            file_name = ospath.basename(file_path)
            new_path  = shortFileName(file_path)
            os.rename(file_path, new_path)
            BotTimes.current_time = time()
            Messages.status_head  = f"<b>📤 UPLOADING</b>\n\n<code>{file_name}</code>\n"
            try:
                MSG.status_msg = await MSG.status_msg.edit_text(
                    text=Messages.task_msg + Messages.status_head
                    + "\n⏳ <i>Starting...</i>" + sysINFO(),
                    reply_markup=keyboard(),
                )
            except Exception: pass
            file_size = os.stat(new_path).st_size
            await upload_file(new_path, file_name, is_last=is_last)
            Transfer.up_bytes.append(file_size)

            if remove and ospath.exists(new_path):
                os.remove(new_path)
            elif not remove:
                for fi in os.listdir(Paths.temp_files_dir):
                    os.remove(ospath.join(Paths.temp_files_dir, fi))

    # Cleanup
    if remove and ospath.exists(folder_path):
        shutil.rmtree(folder_path)
    for d in (Paths.thumbnail_ytdl, Paths.temp_files_dir):
        if ospath.exists(d):
            shutil.rmtree(d)


async def Zip_Handler(down_path: str, is_split: bool, remove: bool):
    Messages.status_head = f"<b>🗜️ COMPRESSING</b>\n\n<code>{Messages.download_name}</code>\n"
    try:
        MSG.status_msg = await MSG.status_msg.edit_text(
            text=Messages.task_msg + Messages.status_head + sysINFO(),
            reply_markup=keyboard(),
        )
    except Exception: pass
    if not ospath.exists(Paths.temp_zpath):
        makedirs(Paths.temp_zpath)
    await archive(down_path, is_split, remove)
    await sleep(2)
    Transfer.total_down_size = getSize(Paths.temp_zpath)
    if remove and ospath.exists(down_path):
        shutil.rmtree(down_path)


async def Unzip_Handler(down_path: str, remove: bool):
    Messages.status_head = f"<b>📂 EXTRACTING</b>\n\n<code>{Messages.download_name}</code>\n"
    try:
        MSG.status_msg = await MSG.status_msg.edit_text(
            text=Messages.task_msg + Messages.status_head
            + "\n⏳ <i>Starting...</i>" + sysINFO(),
            reply_markup=keyboard(),
        )
    except Exception: pass
    filenames = natsorted([str(p) for p in pathlib.Path(down_path).glob("**/*") if p.is_file()])
    for f in filenames:
        short_path = ospath.join(down_path, f)
        if not ospath.exists(Paths.temp_unzip_path):
            makedirs(Paths.temp_unzip_path)
        _, ext = ospath.splitext(ospath.basename(f).lower())
        try:
            if ospath.exists(short_path):
                if ext in [".7z", ".gz", ".zip", ".rar", ".001", ".tar", ".z01"]:
                    await extract(short_path, remove)
                else:
                    shutil.copy(short_path, Paths.temp_unzip_path)
        except Exception as e:
            logging.warning(f"Unzip error: {e}")
    if remove:
        shutil.rmtree(down_path)


async def cancelTask(reason: str):
    spent = getTime((datetime.now() - BotTimes.start_time).seconds)
    text  = (
        "╔━━━━━━━━━━━━━━━━━━━━━━╗\n"
        "║  ⛔  TASK  STOPPED   ║\n"
        "╚━━━━━━━━━━━━━━━━━━━━━━╝\n\n"
        f"  ❓ <b>Reason</b>  <i>{reason}</i>\n"
        f"  ⏱  <b>Spent</b>   <code>{spent}</code>"
    )
    if BOT.State.task_going:
        try:
            BOT.TASK.cancel()           # type: ignore
            shutil.rmtree(Paths.WORK_PATH)
        except Exception as e:
            logging.warning(f"Cancel cleanup: {e}")
        finally:
            BOT.State.task_going = False
            try:
                await MSG.status_msg.edit_text(text)
            except Exception:
                try:
                    await colab_bot.send_message(chat_id=OWNER, text=text)
                except Exception:
                    pass


async def SendLogs(is_leech: bool):
    """
    All completion info is already on the video caption (✅ Done · name).
    We only need to reset bot state here.
    """
    BOT.State.started    = False
    BOT.State.task_going = False
