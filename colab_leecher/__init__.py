import logging
import json
import asyncio
import uvloop
from pyrogram.client import Client

# ─────────────────────────────────────────
# Load credentials from JSON
# ─────────────────────────────────────────
with open("/content/zilong/credentials.json", "r") as file:
    credentials = json.load(file)

API_ID = credentials["API_ID"]
API_HASH = credentials["API_HASH"]
BOT_TOKEN = credentials["BOT_TOKEN"]
OWNER = credentials["USER_ID"]
DUMP_ID = credentials["DUMP_ID"]

logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────
# Proper uvloop + event loop setup
# (fixes: RuntimeError: There is no current event loop in thread 'MainThread')
# ─────────────────────────────────────────
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ─────────────────────────────────────────
# Create Pyrogram client
# ─────────────────────────────────────────
colab_bot = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

logging.info("✅ colab_bot client created")
