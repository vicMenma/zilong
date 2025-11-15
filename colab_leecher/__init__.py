import logging
import json
import asyncio
from uvloop import install
from pyrogram.client import Client

# Read the dictionary from the txt file
with open("/content/zilong/credentials.json", "r") as file:
    credentials = json.loads(file.read())

API_ID = credentials["API_ID"]
API_HASH = credentials["API_HASH"]
BOT_TOKEN = credentials["BOT_TOKEN"]
OWNER = credentials["USER_ID"]
DUMP_ID = credentials["DUMP_ID"]

logging.basicConfig(level=logging.INFO)

# Install uvloop as the event loop policy
install()

# 🔥 Create and set an event loop for the main thread
asyncio.set_event_loop(asyncio.new_event_loop())

# Now it's safe to create the Pyrogram client
colab_bot = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
