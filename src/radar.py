#!/usr/bin/python

## format as..
#MSG,8,111,11111,405B77,111111,2015/04/15,08:19:34.893,2015/04/15,08:19:34.886,,,,,,,,,,,,0
#MSG,7,111,11111,405B77,111111,2015/04/15,08:19:35.154,2015/04/15,08:19:35.148,,24000,,,,,,,,,,0
#MSG,6,111,11111,405B77,111111,2015/04/15,08:19:35.255,2015/04/15,08:19:35.218,BEE8WQ  ,,,,,,,7634,0,0,0,0
#MSG,5,111,11111,40649F,111111,2015/04/15,08:19:35.612,2015/04/15,08:19:35.606,,25700,,,,,,,0,,0,0
#MSG,7,111,11111,40649F,111111,2015/04/15,08:19:35.880,2015/04/15,08:19:35.869,,25725,,,,,,,,,,0


import curses
from datetime import datetime
from plane import Plane
import socket
import thread
import threading
import time

planes = {}
cols = 155
rows = 28
die = False

def removeplanes():
    """ Remove any plane with eventdate older than 30s """
    tozap = []
    for id in planes:
        plane = planes[id]
        if (datetime.utcnow()-plane.eventdate).total_seconds() > 30:
            tozap.append(id)	
	
    for id in tozap:
        del planes[id]

def getplanes(lock, run):
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
    c_socket.connect(('localhost', 30003));

    for line in c_socket.makefile('r'):
        if not run['run']:
            return
        parts = [x.strip() for x in line.split(',')]
        if parts[0] == 'MSG':
            id = parts[4]
            lock.acquire()
            if id in planes:
                plane = planes[id]
            else:
                plane = Plane(parts[4], datetime.utcnow())
                planes[id] = plane
            plane.update(parts)
            lock.release()


def showplanes(win, lock, run):
    while run['run']:
        time.sleep(.400)
        row = 2
        win.erase()
        Plane.showheader(win)
        lock.acquire()
        for id in sorted(planes, key=planes.__getitem__):
            if row < rows - 1:
                planes[id].showincurses(win, row)
                row += 1

        now = str(datetime.utcnow())
        try:
            win.addstr(rows-1, cols-5-len(now), now)
            win.addstr(rows-1, cols-45, str(die))
        except:
            pass	
        win.refresh()
        removeplanes()
        lock.release()


def main(screen):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)

    screen.refresh()

    win = curses.newwin(rows, cols, 1, 1)
    win.bkgd(curses.color_pair(1))
    win.box()

    runstate = {'run':True}
    lock = thread.allocate_lock()
    get = threading.Thread(target=getplanes, args=(lock, runstate ))
    show = threading.Thread(target=showplanes, args=(win, lock, runstate ))
    get.start()
    show.start()
    c = screen.getch()
    runstate['run'] = False
    time.sleep(1)
    
try:
    curses.wrapper(main)
except:
    exit()

	
