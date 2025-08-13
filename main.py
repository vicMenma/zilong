# @title 🖥️ Zilong Code

# @title Main Code
# @markdown <div><center><img src="" height=80></center></div>
# @markdown <center><h4><a>READ</a> How to use</h4></center>

# @markdown <br>

API_ID = 0  # @param {type: "integer"}
API_HASH = ""  # @param {type: "string"}
BOT_TOKEN = ""  # @param {type: "string"}
USER_ID = 0  # @param {type: "integer"}
DUMP_ID = ""  # @param {type: "string"}


import subprocess, time, json, shutil, os
from IPython.display import clear_output
from threading import Thread

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
        print("\r" + "░"*white + "▒▒"+ "▓"*black + "▒▒" + "░"*white, end="")
        black = (black + 2) % 75
        white = (white -1) if white != 0 else 37
        time.sleep(2)
    clear_output()


_Thread = Thread(target=Loading, name="Prepare", args=())
_Thread.start()

if len(str(DUMP_ID)) == 10 and "-100" not in str(DUMP_ID):
    n_dump = "-100" + str(DUMP_ID)
    DUMP_ID = int(n_dump)

if os.path.exists("/content/sample_data"):
    shutil.rmtree("/content/sample_data")

cmd = "git clone https://github.com/vicMenma/zilong.git"
proc = subprocess.run(cmd, shell=True)
cmd = "apt update && apt install ffmpeg aria2"
proc = subprocess.run(cmd, shell=True)
cmd = "pip3 install -r /content/zilong/requirements.txt"
proc = subprocess.run(cmd, shell=True)

credentials = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "USER_ID": USER_ID,
    "DUMP_ID": DUMP_ID,
}

with open('/content/zilong/credentials.json', 'w') as file:
    file.write(json.dumps(credentials))

Working = False

if os.path.exists("/content/zilong/my_bot.session"):
    os.remove("/content/zilong/my_bot.session") # Remove previous bot session

print("\rStarting Bot....")

!cd /content/zilong && python3 -m colab_leecher #type:ignore
