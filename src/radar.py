#!/usr/bin/python

## message format from dump1090:30003 as..
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
import sys
import copy
import logging
import requests
import sqlite3
import os

planes = {}
registration_queue = []
inactive_queue = []
RADAR24URL = 'http://www.flightradar24.com/data/_ajaxcalls/autocomplete_airplanes.php?&term='

cols = 155
rows = 28

def removeplanes():
    """ Remove any plane with eventdate older than 30s """

    for id in planes:
        plane = planes[id]
        if (datetime.now()-plane.eventdate).total_seconds() > 30 and plane.active:
            plane.active = False	
            inactive_queue.append(id)

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
                plane = Plane(id, datetime.now())
                registration_queue.append(id)
                run['session_count'] += 1
                planes[id] = plane
                if len(planes) > run['session_max']:
                    run['session_max'] = len(planes)
            plane.update(parts)
            removeplanes()
            lock.release()


def showplanes(win, lock, run):
    while run['run']:
        time.sleep(.100)
        row = 2
        win.erase()
        Plane.showheader(win)
        lock.acquire()
        for id in sorted(planes, key=planes.__getitem__):
            if planes[id].active:
                if row < rows - 1:
                    planes[id].showincurses(win, row)
                    row += 1
                else:
                    break

        now = str(datetime.now())
        current = 0
        for id in planes:
            if planes[id].active:
                current += 1
                
        try:
            win.addstr(rows-1, 1, 'Current :'+str(current)+' Total (session):'+str(run['session_count'])+' Max (session):'+str(run['session_max']))
            win.addstr(rows-1, cols-5-len(now), now)
        except:
            pass
        
        lock.release()
        win.refresh()

def open_database():
    dbname = os.getenv('REGDBNAME', 'sqlite_planes.db')
    logging.info('Opening db '+dbname)
    return sqlite3.connect(dbname)
     

def close_database(conn):
    logging.info('Closing db')
    sql = 'update observation set endtime="'+str(datetime.now())+'" where endtime is null'
    conn.execute(sql)
    conn.commit()
    conn.close()

def update_registration(reg, id, conn):
    sql = 'insert into registration select "'+id+'", "'+reg+'","'+str(datetime.now())+'"'
    logging.debug('Update db with:'+sql)
    upd = conn.execute(sql)
    conn.commit()
    logging.debug('update result='+str(upd.description))
    
def log_observation_start(id, conn):
    sql = 'insert into observation select ifnull(max(instance)+1,1), "'+id+'","'+str(datetime.now())+'",null from observation where icao_code="'+id+'"'
    logging.debug('adding observation with SQL:'+sql)
    conn.execute(sql)
    conn.commit()

    sql = 'select ifnull(max(instance),1) from observation where icao_code ="'+id+'"'
    crs = conn.cursor()
    crs.execute(sql)
    instance = 0
    for row in crs.fetchall():
        instance, = row

    logging.debug('ICAO '+id+' shows observation instance of '+str(instance))   
    return instance
    
def log_observation_end(id, instance, conn):
    sql = 'update observation set endtime = "'+str(datetime.now())+'" where icao_code = "'+id+'" and endtime is null and instance ='+str(instance)
    logging.debug('ending observation with SQL:'+sql)
    conn.execute(sql)
    conn.commit()
        
def get_registration(id, conn):
    sql = 'select registration from registration where icao_code = "'+id+'"'
    cursor = conn.cursor()
    cursor.execute(sql)
    reg = ''
    for row in cursor.fetchall():
        registration = row
        if len(registration) > 0:
            reg=registration[0]+'*'
            logging.info('Reg '+registration[0]+' in cache')
    if len(reg) == 0:
        # no reg in db, so try FR24 
       reg = get_registration_from_fr24(id)
       if len(reg)>0 and reg != 'x':
           update_registration(reg, id, conn)

    return reg
    
def get_registration_from_fr24(id):
        """ 
        Not sure how long radar24 will keep this REST endpoint exposed 
        But might as well use it while we can
        """
        geturl = RADAR24URL + str(id)
        logging.debug('lookup '+str(id)+' on FR24 via:'+geturl)
        try:
            response = requests.get(geturl)
            if response.status_code == 200:
                return response.json()[0]['id']
            else:
                return ''
        except:
            return 'x'

def get_registrations(lock, runstate):
    conn = open_database()
    while runstate['run']:
        regs = copy.copy(registration_queue)
        for id in regs:
            reg = get_registration(id, conn)
            instance = log_observation_start(id, conn)
            lock.acquire()
            planes[id].registration = reg
            planes[id].observe_instance = instance
            registration_queue.remove(id)
            lock.release()
            
        inactives = copy.copy(inactive_queue)
        for id in inactives:
            try:
                instance = planes[id].observe_instance
                log_observation_end(id, instance, conn)
            except:
                logging.debug('unable to log observation end for id '+str(id))
            lock.acquire()
            inactive_queue.remove(id)
            lock.release()
            
        time.sleep(.500)
    close_database(conn)
    
def main(screen):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
 
    screen.refresh()

    win = curses.newwin(rows, cols, 1, 1)
    win.bkgd(curses.color_pair(1))
    win.box()

    runstate = {'run':True, 'session_count':0, 'session_max':0}
    lock = thread.allocate_lock()
    get = threading.Thread(target=getplanes, args=(lock, runstate ))
    show = threading.Thread(target=showplanes, args=(win, lock, runstate ))
    registration = threading.Thread(target=get_registrations, args=(lock, runstate ))
    
    get.start()
    show.start()
    registration.start()
    
    while runstate['run']:
        ch = screen.getch()
        if ch == 113:
            runstate['run'] = False
        
    time.sleep(2)

# usage: radar.py [screen rows]
if len(sys.argv) > 1:
   rows=int(sys.argv[1])-4
try:
    curses.wrapper(main)
except:
    exit()

	
