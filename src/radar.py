#!/usr/bin/python

## message format from dump1090:30003 as..
# MSG,8,111,11111,405B77,111111,2015/04/15,08:19:34.893,2015/04/15,08:19:34.886,,,,,,,,,,,,0
# MSG,7,111,11111,405B77,111111,2015/04/15,08:19:35.154,2015/04/15,08:19:35.148,,24000,,,,,,,,,,0
# MSG,6,111,11111,405B77,111111,2015/04/15,08:19:35.255,2015/04/15,08:19:35.218,BEE8WQ  ,,,,,,,7634,0,0,0,0
# MSG,5,111,11111,40649F,111111,2015/04/15,08:19:35.612,2015/04/15,08:19:35.606,,25700,,,,,,,0,,0,0
# MSG,7,111,11111,40649F,111111,2015/04/15,08:19:35.880,2015/04/15,08:19:35.869,,25725,,,,,,,,,,0


import ConfigParser
import copy
import curses
import logging
import socket
import sqlite3
import sys
import thread
import threading
import time
from datetime import datetime

import requests
import urllib3.contrib.pyopenssl

from plane import Plane

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


def mark_all_inactive():
    for id in planes:
        plane = planes[id]
        plane.active = False


def getplanes(lock, run, config):
    connected = False
    while run['run']:
        try:
            while not connected:
                try:
                    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    c_socket.connect((config.get('dump1090','host'), int(config.get('dump1090', 'port'))))
                    c_socket.settimeout(float(config.get('dump1090', 'timeout')))
                    connected = True
                except socket.error, err:
                    logging.debug('Failed to connect - err {}'.format(err))
                    time.sleep(1.0)

            lines = c_socket.recv(4096)
            for line in lines.strip().split('\n'):
                if len(line.strip()) < 1:
                    connected = False
                    c_socket.close()
                    break
                else:
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
                        lock.acquire()
                        # grungy way to clear all planes
                        logging.debug('Clear all active queue')
                        inactive_queue = []
                        mark_all_inactive()
                        lock.release()
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

        now = str(datetime.now())[:19]
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


def update_registration(reg, id, equip, conn):
    logging.debug('reg: {reg} equip: {equip}'.format(reg=reg, equip=equip))
    sql = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}")'\
        .format(icao=str(id), reg=str(reg), equip=str(equip), dt=str(datetime.now()))
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
    equip = ''

    if id in reg_cache.keys():
        reg = reg_cache[id][0] + '*'
        equip = reg_cache[id][1]
        instance = reg_cache[id][2]
        logging.info('Registration {} instance {} in cache'.format(reg[:-1], instance))
    else:
        sql = 'select registration, equip from registration where icao_code = "' + id + '"'
        cursor = conn.cursor()
        cursor.execute(sql)

        for row in cursor.fetchall():
            registration, equip, = row
            if len(registration) > 0:
                reg_cache[id] = registration, equip, 0
                instance = 0
                reg = registration + '*'
                logging.info('Reg ' + registration + ' in DB')
        if len(reg) == 0:
            # no reg in db, so try FR24 
            reg, equip, = get_registration_from_fr24(id, config)
            logging.debug('fr24reg returned reg:{reg} equip:{equip}'.format(reg=reg, equip=equip))
            if len(reg) > 0 and reg != '':
                reg_cache[id] = reg, equip, 0
                instance = 0
                update_registration(reg, id, equip, conn)

    return (reg, equip, instance)


def get_registration_from_fr24(id, config):
    """
    Not sure how long radar24 will keep this REST endpoint exposed
    But might as well use it while we can
    """
    url = config.get('fr24', 'api')
    geturl = url.format(str(id))
    logging.debug('lookup ' + str(id) + ' on FR24 via:' + geturl)
    reg = ''
    equip = ''
    try:
        response = requests.get(geturl)
        logging.debug(response.json()['results'])
        if response.status_code == 200:
            try:
                reg = response.json()['results'][0]['id']
                for result in response.json()['results']:
                    if 'detail' in result and 'equip' in result['detail']:
                        equip = result['detail']['equip']
                        if equip is not None:
                            break
                return reg, equip
            except KeyError:
                return reg, equip
        else:
            return reg, equip
    except:
        return reg, equip

    return reg, equip


def get_locations(conn):
    """ Load my recognizeable locations from location table in db """

    locations = {}
    crsr = conn.cursor()
    crsr.execute('select * from location')
    for row in crsr.fetchall():
        place, lat, long, = row
        locations[place] = (lat, long)

    return locations


def get_planes_of_interest(conn):
    """ Load my recognizeable planes from plane_of_interest table in db """

    planes = []
    crsr = conn.cursor()
    crsr.execute('select callsign from plane_of_interest')
    for row in crsr.fetchall():
        callsign, = row
        planes.append(callsign)

    return planes


def warm_reg_cache(conn):
    crsr = conn.cursor()
    crsr.execute('select r.icao_code, r.registration, r.equip, max(o.instance) ' \
                 'from registration r, observation o where r.icao_code = o.icao_code group by r.icao_code, r.registration')
    cache = {}
    for row in crsr.fetchall():
        icao, reg, equip, instance, = row
        cache[icao] = (reg, equip, instance)

    logging.info('Loaded {} registrations into cache'.format(len(cache)))
    return cache


def get_registrations(lock, runstate, config):
    conn = open_database(config)
    locations_from_db = get_locations(conn)
    if len(locations_from_db) > 0:
        logging.info('Loaded {} reference locations into cache'.format(len(locations_from_db)))
        Plane.locations = locations_from_db
    planes_of_interest = get_planes_of_interest(conn)
    if len(planes_of_interest) > 0:
        logging.info('Loaded {} planes of interest into cache'.format(len(planes_of_interest)))
        Plane.planes_of_interest = planes_of_interest

    reg_cache = warm_reg_cache(conn)

    while runstate['run']:
        if len(registration_queue) > 0 or len(inactive_queue) > 0:
            logging.debug('RegQ: {} InactiveQ: {}'.format(len(registration_queue), len(inactive_queue)))
        regs = copy.copy(registration_queue)
        for id in regs:
            reg, equip, curr_instance = get_registration(id, conn, reg_cache, config)
            instance = log_observation_start(id, conn, curr_instance)
            reg_cache[id] = (reg, instance)
            lock.acquire()
            planes[id].registration = reg
            planes[id].observe_instance = instance
            planes[id].equip = equip
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
    config.read('dump1090curses.local.props')

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
