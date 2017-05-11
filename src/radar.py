#!/usr/bin/python

## message format from dump1090:30003 as..
# MSG,8,111,11111,405B77,111111,2015/04/15,08:19:34.893,2015/04/15,08:19:34.886,,,,,,,,,,,,0
# MSG,7,111,11111,405B77,111111,2015/04/15,08:19:35.154,2015/04/15,08:19:35.148,,24000,,,,,,,,,,0
# MSG,6,111,11111,405B77,111111,2015/04/15,08:19:35.255,2015/04/15,08:19:35.218,BEE8WQ  ,,,,,,,7634,0,0,0,0
# MSG,5,111,11111,40649F,111111,2015/04/15,08:19:35.612,2015/04/15,08:19:35.606,,25700,,,,,,,0,,0,0
# MSG,7,111,11111,40649F,111111,2015/04/15,08:19:35.880,2015/04/15,08:19:35.869,,25725,,,,,,,,,,0


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
import ConfigParser
import urllib3.contrib.pyopenssl

planes = {}
registration_queue = []
inactive_queue = []

cols = 155
rows = 28


def removeplanes():
    """ Remove any plane with eventdate older than 30s """

    for id in planes:
        plane = planes[id]
        if (datetime.now() - plane.eventdate).total_seconds() > 30 and plane.active:
            plane.active = False
            logging.debug('add plane id:' + id + ' to inactive queue')
            inactive_queue.append(id)


def getplanes(lock, run, config):
    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c_socket.connect(('localhost', int(config.get('dump1090', 'port'))))
    c_socket.settimeout(float(config.get('dump1090', 'timeout')))

    while run['run']:
        try:
            lines = c_socket.recv(4096)
            for line in lines.strip().split('\n'):
                if len(line.strip()) > 0:
                    logging.debug('got line:' + line.strip())
                    parts = [x.strip() for x in line.split(',')]
                    if parts[0] == 'MSG' and parts[4] != '000000':
                        id = parts[4]
                        lock.acquire()
                        if id in planes:
                            plane = planes[id]
                        else:
                            plane = Plane(id, datetime.now())
                            registration_queue.append(id)
                            run['session_count'] += 1
                            planes[id] = plane

                        plane.update(parts)
                        removeplanes()
                        lock.release()
                    elif parts[0] == 'MSG' and parts[4] == '000000' and int(parts[1]) == 7:
                        removeplanes()
                    elif parts[0] == 'STA':
                        id = parts[4]
                        status = parts[10]
                        if status == 'RM':
                            plane = planes[id]
                            plane.active = False
                            logging.debug('set id: ' + id + ' inactive due to dump1090 remove')
            inactive_queue.append(id)

        except:
            pass
    logging.debug('exit getplanes')


def showplanes(win, lock, run):
    max_distance = 0
    while run['run']:
        time.sleep(.200)
        row = 2
        win.erase()
        Plane.showheader(win)
        # lock.acquire()
        cached = 0

        for id in sorted(planes, key=planes.__getitem__):
            if planes[id].active:
                if row < rows - 1:
                    planes[id].showincurses(win, row)
                    if planes[id].from_antenna > max_distance:
                        max_distance = planes[id].from_antenna

                    if planes[id].registration[-1:] == '*':
                        cached += 1
                    row += 1
                else:
                    break

        now = str(datetime.now())
        current = 0
        for id in planes:
            if planes[id].active:
                current += 1

        if current > run['session_max']:
            run['session_max'] = len(planes)

        try:
            coverage = cached * 100 / current
        except:
            coverage = 0

        try:
            win.addstr(rows - 1, 1,
                       'Current:{}  Total (session):{}  Max (session):{}  Reg Cache:{}%  Max Distance:{:3.1f}nm'.format(
                           str(current), str(run['session_count']), str(run['session_max']), str(int(coverage)),
                           max_distance))
            win.addstr(rows - 1, cols - 5 - len(now), now)
        except:
            pass

        # lock.release()
        win.refresh()


def open_database(config):
    dbname = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
    logging.info('Opening db ' + dbname)
    return sqlite3.connect(dbname)


def close_database(conn):
    logging.info('Closing db')
    sql = 'update observation set endtime="' + str(datetime.now()) + '" where endtime is null'
    conn.execute(sql)
    conn.commit()
    conn.close()


def update_registration(reg, id, conn):
    sql = 'insert into registration select "' + id + '", "' + reg + '","' + str(datetime.now()) + '"'
    logging.debug('Update db with:' + sql)
    upd = conn.execute(sql)
    conn.commit()
    logging.debug('update result=' + str(upd.description))


def log_observation_start(id, conn, curr_instance):
    sql = 'insert into observation select "' + str(curr_instance + 1) + '","' + id + '","' + str(
        datetime.now()) + '",null '
    logging.debug('adding observation with SQL:' + sql)
    conn.execute(sql)
    conn.commit()

    # sql = 'select max(instance) from observation where icao_code ="'+id+'"'
    # crs = conn.cursor()
    # crs.execute(sql)
    # instance = 0
    # for row in crs.fetchall():
    #   instance, = row

    # logging.debug('ICAO '+id+' shows observation instance of '+str(instance))
    return curr_instance + 1


def log_observation_end(id, instance, conn):
    sql = 'update observation set endtime = "' + str(
        datetime.now()) + '" where icao_code = "' + id + '" and endtime is null and instance =' + str(instance)
    logging.debug('ending observation with SQL:' + sql)
    conn.execute(sql)
    conn.commit()


def get_registration(id, conn, reg_cache, config):
    reg = ''
    instance = 0

    if id in reg_cache.keys():
        reg = reg_cache[id][0] + '*'
        instance = reg_cache[id][1]
        logging.info('Registration {} instance {} in cache'.format(reg[:-1], instance))
    else:
        sql = 'select registration from registration where icao_code = "' + id + '"'
        cursor = conn.cursor()
        cursor.execute(sql)

        for row in cursor.fetchall():
            registration = row
            if len(registration) > 0:
                reg_cache[id] = registration[0]
                instance = 0
                reg = registration[0] + '*'
                logging.info('Reg ' + registration[0] + ' in DB')
        if len(reg) == 0:
            # no reg in db, so try FR24 
            reg = get_registration_from_fr24(id, config)
            if len(reg) > 0 and reg != 'x':
                reg_cache[id] = reg
                instance = 0
                update_registration(reg, id, conn)

    return (reg, instance)


def get_registration_from_fr24(id, config):
    """
    Not sure how long radar24 will keep this REST endpoint exposed
    But might as well use it while we can
    """
    url = config.get('fr24', 'api')
    geturl = url.format(str(id))
    logging.debug('lookup ' + str(id) + ' on FR24 via:' + geturl)
    try:
        response = requests.get(geturl)
        logging.debug(response.json()['results'])
        if response.status_code == 200:
            try:
                return response.json()['results'][0]['id']
            except KeyError:
                return ''
        else:
            return ''
    except:
        return 'x'


def get_locations(conn):
    """ Load my recognizeable locations from location table in db """

    locations = {}
    crsr = conn.cursor()
    crsr.execute('select * from location')
    for row in crsr.fetchall():
        place, lat, long, = row
        locations[place] = (lat, long)

    return locations


def warm_reg_cache(conn):
    crsr = conn.cursor()
    crsr.execute('select r.icao_code, r.registration, max(o.instance) ' \
                 'from registration r, observation o where r.icao_code = o.icao_code group by r.icao_code, r.registration')
    cache = {}
    for row in crsr.fetchall():
        icao, reg, instance, = row
        cache[icao] = (reg, instance)

    logging.info('Loaded {} registrations into cache'.format(len(cache)))
    return cache


def get_registrations(lock, runstate, config):
    conn = open_database(config)
    locations_from_db = get_locations(conn)
    if len(locations_from_db) > 0:
        Plane.locations = locations_from_db

    reg_cache = warm_reg_cache(conn)

    while runstate['run']:
        regs = copy.copy(registration_queue)
        for id in regs:
            reg, curr_instance = get_registration(id, conn, reg_cache, config)
            instance = log_observation_start(id, conn, curr_instance)
            reg_cache[id] = (reg, instance)
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
                logging.debug('unable to log observation end for id ' + str(id))
            lock.acquire()
            inactive_queue.remove(id)
            lock.release()

        time.sleep(.0500)
    close_database(conn)
    logging.debug('exit get_registrations')


def main(screen):
    urllib3.contrib.pyopenssl.inject_into_urllib3()
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')
    dt = str(datetime.now())[:10]

    logging.basicConfig(format='%(asctime)s %(message)s',
                        filename=config.get('directories', 'log') + '/' + config.get('logging',
                                                                                     'logname') + dt + '.log',
                        level=logging.DEBUG)
    logging.captureWarnings(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    prev_state = curses.curs_set(0)

    screen.refresh()

    win = curses.newwin(rows, cols, 1, 1)
    win.bkgd(curses.color_pair(1))
    win.box()

    runstate = {'run': True, 'session_count': 0, 'session_max': 0}
    lock = thread.allocate_lock()
    get = threading.Thread(target=getplanes, args=(lock, runstate, config))
    show = threading.Thread(target=showplanes, args=(win, lock, runstate))
    registration = threading.Thread(target=get_registrations, args=(lock, runstate, config))

    get.start()
    show.start()
    registration.start()

    while runstate['run']:
        ch = screen.getch()
        if ch == 113:
            runstate['run'] = False
            logging.debug('kill requested by user')

    time.sleep(2)
    curses.curs_set(prev_state)


# usage: radar.py [screen rows]
if len(sys.argv) > 1:
    rows = int(sys.argv[1]) - 4
try:
    curses.wrapper(main)
except:
    exit()
