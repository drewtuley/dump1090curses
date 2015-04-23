#!/usr/bin/python

## format as..
#MSG,8,111,11111,405B77,111111,2015/04/15,08:19:34.893,2015/04/15,08:19:34.886,,,,,,,,,,,,0
#MSG,7,111,11111,405B77,111111,2015/04/15,08:19:35.154,2015/04/15,08:19:35.148,,24000,,,,,,,,,,0
#MSG,6,111,11111,405B77,111111,2015/04/15,08:19:35.255,2015/04/15,08:19:35.218,BEE8WQ  ,,,,,,,7634,0,0,0,0
#MSG,5,111,11111,40649F,111111,2015/04/15,08:19:35.612,2015/04/15,08:19:35.606,,25700,,,,,,,0,,0,0
#MSG,7,111,11111,40649F,111111,2015/04/15,08:19:35.880,2015/04/15,08:19:35.869,,25725,,,,,,,,,,0


import socket,os, curses
from plane import Plane
from datetime import datetime

planes={}
cols=145
rows=20

def removeplanes():
	""" Remove any plane with eventdate older than 30s """
	tozap=[]
	for id in planes:
		plane=planes[id]
		if (datetime.utcnow()-plane.eventdate).total_seconds() > 30:
			tozap.append(id)	
	
	for id in tozap:
		del planes[id]

def main(screen):
	curses.start_color()
	curses.init_pair(1,curses.COLOR_GREEN, curses.COLOR_BLUE)

	screen.refresh()
	c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
	c_socket.connect(('localhost',30003));

	win = curses.newwin(rows,cols,1,1)
	win.bkgd(curses.color_pair(1))
	win.box()
	for line in c_socket.makefile('r'):
		#print line
		parts=[x.strip() for x in line.split(',')]
		if parts[0] == 'MSG':
			id = parts[4]
			if id in planes:
				plane =planes[id]
			else:
				plane = Plane(parts[4], datetime.utcnow())
				planes[id]=plane
			plane.update(parts)

			removeplanes()

			row=2
			win.erase()
			plane.showheader(win)

			for id in sorted(planes, key=planes.__getitem__):
				planes[id].showincurses(win, row)
				row=row+1

			now=str(datetime.utcnow())
			win.addstr(rows-1,cols-5-len(now),now)
			win.refresh()

try:
	curses.wrapper(main)
except KeyboardInterrupt:
	exit()

	
