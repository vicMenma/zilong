# @title 🖥️ Zilong Code

# @title Main Code
# @markdown <div><center><img src="" height=80></center></div>
# @markdown <center><h4><a>READ</a> How to use</h4></center>
# @markdown <br>

API_ID = 0        # @param {type: "integer"}
API_HASH = ""     # @param {type: "string"}
BOT_TOKEN = ""    # @param {type: "string"}
USER_ID = 0       # @param {type: "integer"}
DUMP_ID = ""      # @param {type: "string"}

import os
import time
import json
import shutil
import subprocess
from threading import Thread
from IPython.display import clear_output

Working = True

banner = '''
 ███████╗██╗██╗██╗      ██████╗ ███╗   ██╗ ██████╗ 
 ╚══███╔╝██║██║██║     ██╔═══██╗████╗  ██║██╔════╝ 
   ███╔╝ ██║██║██║     ██║   ██║██╔██╗ ██║██║  ███╗
  ███╔╝  ██║██║██║     ██║   ██║██║╚██╗██║██║   ██║
 ███████╗██║██║███████╗╚██████╔╝██║ ╚████║╚██████╔╝
 ╚══════╝╚═╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ 
                                                    
  ██████╗ ██████╗ ██████╗ ███████╗                 
 ██╔════╝██╔═══██╗██╔══██╗██╔════╝                 
 ██║     ██║   ██║██║  ██║█████╗                   
 ██║     ██║   ██║██║  ██║██╔══╝                   
 ╚██████╗╚██████╔╝██████╔╝███████╗                 
  ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝                 
'''
print(banner)


def Loading():
    white = 37
    black = 0
    while Working:
        print("\r" + "░" * white + "▒▒" + "▓" * black + "▒▒" + "░" * white, end="")
        black = (black + 2) % 75
        white = (white - 1) if white != 0 else 37
        time.sleep(2)
    clear_output()


_thread = Thread(target=Loading, name="Prepare", args=())
_thread.start()

# Normalize DUMP_ID to -100xxxxxxxxxx format if needed
if len(str(DUMP_ID)) == 10 and "-100" not in str(DUMP_ID):
    DUMP_ID = int("-100" + str(DUMP_ID))

# Clean default Colab sample folder
if os.path.exists("/content/sample_data"):
    shutil.rmtree("/content/sample_data")

# Clone repo (if already exists, you can delete or skip manually)
subprocess.run(
    "git clone https://github.com/vicMenma/zilong.git",
    shell=True,
    check=True,
)

# Install system dependencies
subprocess.run(
    "apt update && apt install -y ffmpeg aria2",
    shell=True,
    check=True,
)

# Install Python dependencies
subprocess.run(
    "pip3 install -r /content/zilong/requirements.txt",
    shell=True,
    check=True,
)

# Write credentials for colab_leecher/__init__.py
credentials = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "USER_ID": USER_ID,
    "DUMP_ID": DUMP_ID,
}

os.makedirs("/content/zilong", exist_ok=True)
with open("/content/zilong/credentials.json", "w", encoding="utf-8") as file:
    json.dump(credentials, file)

# Stop loading animation
Working = False
_thread.join(timeout=2)

# Remove previous bot session if any
session_file = "/content/zilong/my_bot.session"
if os.path.exists(session_file):
    os.remove(session_file)

print("\rStarting Bot....")

# Start bot as a normal subprocess (no notebook magic)
subprocess.run(
    ["python3", "-m", "colab_leecher"],
    cwd="/content/zilong",
    check=True,
)
