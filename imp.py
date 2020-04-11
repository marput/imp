#!/usr/bin/env python 
import urwid
import urllib
import shutil
import sys
import time
import random
import argparse
import os
import requests
import re
import tempfile
import subprocess
import json
import datetime
#from common import getRandomUserAgent
#from common import getUserAgents
from collections import deque

CHANGE_PAGE = False
GO_NEXT = False
GO_BACK = False
message_timeout = 1

small_logo = " _____ ___  _________ \n|_   _||  \/  || ___ \\\n  | |  | .  . || |_/ /\n  | |  | |\/| ||  __/ \n _| |_ | |  | || |    \n \___/ \_|  |_/\_|    \n"

api_base_search = "https://invidio.us/api/v1/search?sort_by=relevance&type=video"

palette = [
    ('reversed', 'bold,light gray', 'black'),
    ('heading', 'black', 'light gray'),
    ('line', 'black', 'light gray'),
    ('options', 'dark gray', 'black'),
    ('focus heading', 'white', 'dark red'),
    ('focus line', 'black', 'dark red'),
    ('focus options', 'black', 'white'),
    ('selected', 'white', 'white')]


#=====================================================
#ACTIONS                                             |
#=====================================================

def nextSong(button=None):
    global current_song, previous_songs, next_songs, GO_NEXT
    GO_NEXT = True
    p.kill()
    previous_songs.append(current_song)
    if len(next_songs) > 0:
        current_song = next_songs.pop()
    else:
        current_song = random.choice(songs)

def previousSong(button=None):
    global current_song, previous_songs, next_songs, GO_BACK
    GO_BACK = True
    p.kill()
    next_songs.append(current_song)
    try:
        current_song = previous_songs.pop()
    except IndexError:
        try: #if no previous song, play next song on stack
            current_song = next_songs.pop()
        except IndexError: #if the current song is the first ever, play random song
            current_song = random.choice(songs)

def download(button=None):
    destination = os.path.join(os.path.expanduser(args.path), "'%(title)s.%(ext)s'")
    subprocess.Popen(["youtube-dl", "-x", "-o", destination, "--audio-quality", "0", "--audio-format", "mp3", href], stderr = subprocess.DEVNULL, stdout = subprocess.DEVNULL)
    showMessage("download", "Downloading!", message_timeout, loop, info)

#def filterTitle(button=None):
#    edit = urwid.Edit(u"Enter the filter\n", edit_text='', align='center')
#    box = InputBox(edit)
#    menu_object.original_widget = box

def filterTitle(button=None):
    if args.sfilter:
        with open(os.path.abspath(os.path.expanduser(args.sfilter)), "a") as infile:
            infile.write('\n' + re.escape(title) + '\n')
        showMessage("filtered", "Added title to filter!", message_timeout, loop, info)
    elif args.filters:
        pass
    else:
        showMessage("no_filter", "Can't filter, no filter file available!", message_timeout, loop, info)

def loopSong(button=None):
    global loop, info
    a = subprocess.getoutput('echo \'{ "command": ["get_property", "loop-file"] }\' | socat - ' + socket_path)
    j = json.loads(a) #json loads
    if j['data'] == False:
        subprocess.getoutput('echo \'{ "command": ["set_property", "loop-file", true] }\' | socat - ' + socket_path)
        showMessage("loop_on", "Loop on!", message_timeout, loop, info)
    else:
        subprocess.getoutput('echo \'{ "command": ["set_property", "loop-file", false] }\' | socat - ' + socket_path)
        showMessage("loop_off", "Loop off!", message_timeout, loop, info)

def randomPage(button=None):
    p.kill()
    raise StopIteration()

def changePageMenu(button=None):
    global page, CHANGE_PAGE
    edit = urwid.Edit(u"Enter the page number\n", edit_text='', align='center')
    temp = InputBox(edit)
    p.kill()
    loop = urwid.MainLoop(temp, palette, unhandled_input = handle_menu_choice)
    loop.set_alarm_in(10, terminateUrwidLoop)
    loop.run()
    try:
        page = int(edit.edit_text)
    except:
        page = random.randint(1, highest_page)
    CHANGE_PAGE = True
    raise StopIteration()

def pause(button=None):
    a = subprocess.getoutput('echo \'{ "command": ["get_property", "pause"] }\' | socat - ' + socket_path)
    j = json.loads(a) #json loads
    if j['data'] == False:
        subprocess.getoutput('echo \'{"command": ["cycle", "pause"] }\' | socat - ' + socket_path)
        showMessage("paused", "Paused!", message_timeout, loop, info)
    else:
        subprocess.getoutput('echo \'{"command": ["cycle", "pause"] }\' | socat - ' + socket_path)
        showMessage("started", "Started!", message_timeout, loop, info)

def shutdown(button=None):
    p.kill()
    sys.exit(0)

def copyTitle(button=None):
    echo = subprocess.Popen(['echo', title], stdout=subprocess.PIPE)
    subprocess.call(['xclip', '-sel', 'cli'], stdin=echo.stdout)
    showMessage("copy_title", "Copied title!", message_timeout, loop, info)

def copyUrl(button=None):
    echo = subprocess.Popen(['echo', href], stdout=subprocess.PIPE)
    subprocess.call(['xclip', '-sel', 'cli'], stdin=echo.stdout)
    showMessage("copy_url", "Copied url!", message_timeout, loop, info)

def handleUrwidLoop(_loop, _data):
    if p.poll() == None: #if a song is playing
        try: #get time position
            duration = str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput("echo '{ \"command\": [\"get_property_string\", \"duration\"] }' | socat - " + socket_path))[0])))
            position = str(datetime.timedelta(seconds=int(re.search(r"[0-9]+", subprocess.getoutput('echo \'{ "command": ["get_property_string", "time-pos"] }\' | socat - ' + socket_path))[0]))) + "/" + duration
        except TypeError: #if it hasnt loaded yet, loop
            loop.set_alarm_in(1, handleUrwidLoop)
            return
        info['time'] = position
        changeMenuString(info)
        loop.draw_screen()
        loop.set_alarm_in(1, handleUrwidLoop)
    else: #if song isn't playing, break loop
        raise urwid.ExitMainLoop()

def terminateUrwidLoop(_loop, _data):
        raise urwid.ExitMainLoop()

#===========================================================

main_menu_buttons = {
    "   [n]ext    ": nextSong,
    "   [p]ause   ": pause,
    "   [b]ack   ": previousSong,
    " [d]ownload  ": download,
    "   [f]ilter  ": filterTitle,
    "   [l]oop   ": loopSong,
    "[r]andom page": randomPage,
    "[c]hange page": changePageMenu,
    "copy [t]itle": copyTitle,
    " copy [u]rl": copyUrl,
    "   [q]uit   ": shutdown,
}

#===========================================================
#ACTUAL BACKEND                                            |
#===========================================================


def toFilter(title):
    with open(os.path.abspath(os.path.expanduser(args.sfilter)), "r") as outfile:
        for line in outfile:
            if re.search(line[:-1], title, re.IGNORECASE): #remove the trailing \n
                return True
    return False

def toFilters(title):
    clean_files = []
    files = args.filters.split(',')
    for path in files:
        clean_files.append(path.strip())
    for path in clean_files:
        with open(os.path.abspath(os.path.expanduser(path)), "r") as outfile:
            for line in outfile:
                if re.search(line[:-1], title, re.IGNORECASE): #remove the trailing \n
                    return True
    return False

def changePage(url, page):
    url = re.subn(r"(page=)\d+", r"\g<1>" + str(page), url)
    if url[1] == 0:
        return url[0] + "&page=" + str(page)
    return url[0]

def getUpperBound(session, url, lower_bound):
    url = changePage(url, lower_bound)
    r = session.get(url)
    if r.json() != []:
        return getUpperBound(session, url, lower_bound*4+1)
    return lower_bound+1

def getHighestPage(session, url, lower_bound, upper_bound):
    middle_page = int((lower_bound+upper_bound)/2)
    middle_url = changePage(url, middle_page)
    middle_site = session.get(middle_url)
    if middle_site.json() != []: #No match
        next_url = changePage(url, middle_page+1)
        next_site = session.get(next_url)
        if next_site.json() != []:
            return middle_page+1
        return getHighestPage(session, url, middle_page+1, upper_bound)
    else: #Match
        previous_url = changePage(url, middle_page-1)
        previous_site = session.get(previous_url)
        if previous_site.json() != []:
            return middle_page-1
        return getHighestPage(session, url, lower_bound, middle_page-1)


#===========================================================

#===========================================================
#MENU/GRAPHICAL STUFF                                      |
#===========================================================

class InputBox(urwid.Filler):
    def __init__(self, edit):
        self.edit = edit
        super().__init__(edit)
    def keypress(self, size, key):
        if key != 'enter':
            return super(InputBox, self).keypress(size, key)
        else:
            raise urwid.ExitMainLoop()

TEXT = urwid.Text(('banner', "Menu"), align='center')

def menu(info={'logo': "Menu"}):
    full_string = ""
    for item in info.values():
        full_string += item + '\n'
    list_of_buttons = []
    for key, value in main_menu_buttons.items():
        button = urwid.Button(key)
        urwid.connect_signal(button, 'click', value)
        button = urwid.AttrMap(button, 'heading', focus_map='reversed')
        list_of_buttons.append(button)
    TEXT.set_text(full_string)
    body = [TEXT, urwid.GridFlow(list_of_buttons, 17, 3, 1, align='center')]
    listbox = urwid.ListBox(body)
    return listbox

def changeMenuString(info):
    full_string = ""
    for item in info.values():
        full_string += item + '\n'
    TEXT.set_text(full_string)

def handle_menu_choice(key):
    if key in ('n', 'N'):
        nextSong()
    elif key in ('p', 'P'):
        pause()
    elif key in ('b', 'B'):
        previousSong()
    elif key in ('d', 'D'):
        download()
    elif key in ('f', 'F'):
        filterTitle()
    elif key in ('l', 'L'):
        loopSong()
    elif key in ('r', 'R'):
        randomPage()
    elif key in ('c', 'C'):
        changePageMenu()
    elif key in ('t', 'T'):
        copyTitle()
    elif key in ('u', 'U'):
        copyUrl()
    elif key in ('q', 'Q'):
        shutdown()

def showMessage(key_name, string, timeout, loop, info):
    info[key_name] = string
    changeMenuString(info)
    loop.draw_screen()
    time.sleep(timeout)
    del(info[key_name])
    changeMenuString(info)

#===========================================================

#Parse the arguments
parser = argparse.ArgumentParser(description = "Command-line tool for streaming random music from invidio.us")

filtering = parser.add_mutually_exclusive_group(required=False)
parser.add_argument("--query", dest = "query", metavar = "STRING", type=str, required = True, help = "Query to search videos by")
parser.add_argument("--path", dest = "path", metavar = "STRING", required=False, type=str, default=os.path.abspath(os.path.curdir), help = "Path where music files will get saved to")
filtering.add_argument("--filter", dest= "sfilter", metavar = "STRING", required=False, type=str, help = "Filter file")
filtering.add_argument("--filters", dest = "filters", metavar = "FILTERS", required = False, type=str, help = "String of filter files separated by commas")
args = parser.parse_args()

#Establish session
session = requests.session()
#print("Setting User Agent...")
#session.headers.update({"User-Agent": getRandomUserAgent(getUserAgents())})

#Get highest page
url = api_base_search + "&q=" + urllib.parse.quote_plus(args.query)
print("Getting upper bound...")
upper_bound = getUpperBound(session, url, 1)
print("Getting highest page...")
highest_page = getHighestPage(session, url, upper_bound/4-1, upper_bound)

while True:
    if CHANGE_PAGE:
        CHANGE_PAGE = False
    else:
        page = random.randint(1, highest_page) 
    url = changePage(url, page)
    r = session.get(url)
    j = r.json()
    songs = [*range(0, len(j))]
    previous_songs = deque()
    next_songs = deque()
    current_song = random.choice(songs)
    try:
        
        while len(songs) > 0:
            info = {}
            temp_dir = tempfile.mkdtemp()
            try:
                href = "https://youtube.com/watch?v=" + j[current_song]['videoId']
            except IndexError:
                current_song += 1
                continue
            title = j[current_song]['title']
            if args.sfilter != None:
                if toFilter(title):
                    songs.remove(current_song)
                    continue
            elif args.filters != None:
                if toFilters(title):
                    songs.remove(current_song)
                    continue
            pageinfo = "Page " + str(page) + " out of " + str(highest_page) + " in total."
            socket_path = os.path.join(temp_dir, "invidiousplayersocket")
            p = subprocess.Popen(["mpv", "--input-ipc-server=" + socket_path, "--no-video", "--ytdl-format=bestaudio", href], stderr = subprocess.DEVNULL, stdout = subprocess.DEVNULL)
            while not os.path.exists(socket_path):
                #Wait for socket to load
                time.sleep(1)
            info['logo'] = small_logo
            info['pageinfo'] = pageinfo
            info['title'] = title
            info['href'] = href
            info['time'] = "00:00/00:00"
            menu_object = menu(info)
            loop = urwid.MainLoop(menu_object, palette, unhandled_input = handle_menu_choice)
            loop.set_alarm_in(0, handleUrwidLoop)
            loop.run()
            shutil.rmtree(temp_dir)
            if not GO_BACK and not GO_NEXT:
                nextSong()
            if GO_BACK:
                GO_BACK = False
            if GO_NEXT:
                GO_NEXT = False
            try:
                songs.remove(current_song)
            except ValueError:
                pass
            
    except StopIteration:
        pass
