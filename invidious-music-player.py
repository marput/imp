import argparse
import os
import subprocess
import time
import requests
import re
import random
import sys
import datetime
import select
import shutil
import tempfile
import errno
from termios import tcflush, TCIOFLUSH
from common import getRandomUserAgent
from common import getUserAgents

api_base_search = "https://invidio.us/api/v1/search?sort_by=relevance&type=video"

session = requests.session()
print("Setting User Agent...")
session.headers.update({"User-Agent": getRandomUserAgent(getUserAgents())})

parser = argparse.ArgumentParser(description = "Command-line tool for streaming random music from invidio.us")

filtering = parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--query", dest = "query", metavar = "STRING", type=str, required = True, help = "Query to search videos by")
parser.add_argument("--path", dest = "path", metavar = "STRING", required=False, type=str, default=os.path.abspath(os.path.curdir), help = "Path where music files will get saved to")
filtering.add_argument("--filter", dest= "sfilter", metavar = "STRING", required=False, type=str, help = "Filter file")
filtering.add_argument("--filters", dest = "filters", metavar = "FILTERS", required = False, type=str, help = "String of filter files separated by commas")

args = parser.parse_args()

if not __debug__:
    print("Query {} Path {} Filter {} Filters {}".format(
        args.query,
        args.path,
        args.sfilter,
        args.filters,
    ))

def changePage(url, page):
    url = re.subn(r"(page=)\d+", r"\g<1>" + str(page), url)
    if url[1] == 0:
        return url[0] + "&page=" + str(page)
    return url[0]

def getUpperBound(session, url, lower_bound):
    url = changePage(url, lower_bound)
    r = session.get(url)
    if r.json() != []:
        print(lower_bound,"is too low...")
        return getUpperBound(session, url, lower_bound*4+1)
    return lower_bound+1

def getHighestPage(session, url, lower_bound, upper_bound):
    middle_page = int((lower_bound+upper_bound)/2)
    middle_url = changePage(url, middle_page)
    middle_site = session.get(middle_url)
    if middle_site.json() != []:
        print("No match")
        next_url = changePage(url, middle_page+1)
        next_site = session.get(next_url)
        if next_site.json() != []:
            return middle_page+1
        return getHighestPage(session, url, middle_page+1, upper_bound)
    else:
        print("Match")
        previous_url = changePage(url, middle_page-1)
        previous_site = session.get(previous_url)
        if previous_site.json() != []:
            return middle_page-1
        return getHighestPage(session, url, lower_bound, middle_page-1)

url = api_base_search + "&q=" + args.query
print("Getting upper bound...")
upper_bound = getUpperBound(session, url, 1)
print("Getting highest page...")
highest_page = getHighestPage(session, url, upper_bound/4-1, upper_bound)

original_path = os.getcwd()
os.chdir("images")
list_of_images = os.listdir(".")
os.chdir(original_path)
prompt = "Press d to download the file, press n to go to the next, press a to add a new filter, press p to pause"
prompttwo = "press r to refresh screen, press c to change page, press q to quit.\n"
columns = os.get_terminal_size().columns

def killProcess(process):
    while process.poll() == None:
        process.kill()
        process.terminate()

def redrawMenu(info, title, href):
    subprocess.call(['clear'])
    for i in range(1, 20):
        print()
    print(info.center(int(columns)))
    print(title.center(int(columns)))
    print(href.center(int(columns)))
    print(prompt.center(int(columns)))
    print(prompttwo.center(int(columns)))

def printTime(time_elapsed, time_total):
    print("\r" + str(str(time_elapsed) + "/" + str(time_total)).center(int(columns)), end="")

def drawImage(image):
    img = subprocess.Popen(["/home/cirno/programming/python/invidious-music-player/displayimage.sh", image])

def pause(socket_path):
    subprocess.getoutput('echo \'{"command": ["cycle", "pause"] }\' | socat - ' + socket_path)
    print("Paused!".center(int(columns)))
    time.sleep(2)

def download():
    destination = os.path.join(args.path, "'%(title)s.%(ext)s'")
    subprocess.Popen(["youtube-dl", "-x", "-o", destination, "--audio-quality", "0", "--audio-format", "mp3", href], stderr = subprocess.DEVNULL, stdout = subprocess.DEVNULL)
    print("Downloading...".center(int(columns)))
    time.sleep(2)

def filterChoice(socket_path):
    if args.sfilter != None or args.filters != None:
        addFilter(title)
    else:
        print("Not running with filter file!".center(int(columns)))
        time.sleep(2)

def menuLoop(p, j, socket_path, temp_dir):
    while p.poll() == None:
        duration = str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput("echo '{ \"command\": [\"get_property_string\", \"duration\"] }' | socat - " + socket_path))[0])))
        printTime(str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput('echo \'{ "command": ["get_property_string", "time-pos"] }\' | socat - ' + socket_path))[0]))), duration)
        if select.select([sys.stdin,], [], [], 0.0)[0]:
            choice = input()
            if choice in ["d", "D"]:
                download()
                choice = ""
                redrawMenu(info, title, href)
                printTime(str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput('echo \'{ "command": ["get_property_string", "time-pos"] }\' | socat - ' + socket_path))[0]))), duration)
            elif choice in ["p", "P"]:
                pause(socket_path)
                choice = ""
                redrawMenu(info, title, href)
                printTime(str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput('echo \'{ "command": ["get_property_string", "time-pos"] }\' | socat - ' + socket_path))[0]))), duration)
            elif choice in ["n", "N"]:
                subprocess.call(['pkill', 'displayimage.sh'])
                p.kill()
                choice = ""
                redrawMenu(info, title, href)
                return
            elif choice in ["a", "A"]:
                filterChoice(socket_path)
                redrawMenu(info, title, href)
                printTime(str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput('echo \'{ "command": ["get_property_string", "time-pos"] }\' | socat - ' + socket_path))[0]))), duration)
                choice = ""
            elif choice in ["c", "C"]:
                subprocess.call(['pkill', 'displayimage.sh'])
                p.kill()
                raise StopIteration()
            elif choice in ["r", "R"]:
                redrawMenu(info, title, href)
            elif choice in ["q", "Q"]:
                subprocess.call(['pkill', 'displayimage.sh'])
                p.kill()
                sys.exit(0)
            redrawMenu(info, title, href)
            printTime(str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput('echo \'{ "command": ["get_property_string", "time-pos"] }\' | socat - ' + socket_path))[0]))), duration)
    time.sleep(1)
    subprocess.call(['pkill', 'displayimage.sh'])


while True:
    random_page = random.randint(1, highest_page)
    url = changePage(url, random_page)
    choice = ""
    r = session.get(url)
    j = r.json()
    try:
        for element in j:
            try:
                temp_dir = tempfile.mkdtemp()
                os.chdir("images")
                image = os.path.abspath(random.choice(list_of_images))
                drawImage(image)
                os.chdir(original_path)
                href = "https://youtube.com/watch?v=" + element['videoId']
                info = "Page " + str(random_page) + " out of " + str(highest_page) + " in total."
        #        title = element['title'] + " (" + str(datetime.timedelta(seconds=int(element['lengthSeconds']))) + ")."
                title = element['title']
                socket_path = os.path.join(temp_dir, "invidiousplayersocket")
                p = subprocess.Popen(["mpv", "--input-ipc-server=" + socket_path, "--no-video", "--af=scaletempo=speed=both", "--audio-pitch-correction=no", "--ytdl-format=bestaudio", href], stderr = subprocess.DEVNULL, stdout = subprocess.DEVNULL)
                while not os.path.exists(socket_path):
                    time.sleep(1)
                redrawMenu(info, title, href)
                menuLoop(p, j, socket_path, temp_dir)
                shutil.rmtree(temp_dir)
            finally:
                try:
                    shutil.rmtree(temp_dir)
                except OSError as exc:
                    if exc.errno != errno.ENOENT:
                        raise
    except StopIteration:
        pass
