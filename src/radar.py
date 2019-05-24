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
import logging.handlers
import socket
import sys
import thread
import threading
import time
from datetime import datetime

import requests

from plane import Plane

planes = {}
registration_queue = []
inactive_queue = []
onoff = {True: 'On', False: 'Off'}

cols = 155
rows = 28


def removeplanes():
    """ Remove any plane with eventdate older than 30s """

    for id in planes:
        plane = planes[id]
        if (datetime.now() - plane.eventdate).total_seconds() > 30 and plane.active:
            plane.active = False
            logger.debug('add plane id:' + id + ' to inactive queue')
            inactive_queue.append(id)


def mark_all_inactive():
    for id in planes:
        plane = planes[id]
        plane.active = False


def getplanes(lock, run, config):
    connected = False
    underrun = ''
    logger.debug('Connected with config: {}'.format(config))
    while run['run']:
        try:
            while not connected:
                try:
                    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    c_socket.connect((config['host'], config['port']))
                    c_socket.settimeout(config['timeout'])
                    connected = True
                except socket.error, err:
                    logger.debug('Failed to connect - err {}'.format(err))
                    time.sleep(1.0)

            lines = c_socket.recv(32768)
            lines = underrun + lines
            underrun = ''
            if len(lines) < 1:
                connected = False
                c_socket.close()
                break
            for line in lines.strip().split('\n'):
                logger.debug('got line:' + line.strip())
                parts = [x.strip() for x in line.split(',')]
                if len(parts) < 22:
                    underrun = line
                    break
                if parts[0] in ('MSG', 'MLAT') and parts[4] != '000000':
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
                    logger.debug('Clear all active queue')
                    inactive_queue = []
                    mark_all_inactive()
                    lock.release()
                elif parts[0] == 'STA':
                    id = parts[4]
                    status = parts[10]
                    if status == 'RM':
                        plane = planes[id]
                        plane.active = False
                        logger.debug('set id: ' + id + ' inactive due to dump1090 remove')
            inactive_queue.append(id)

        except:
            pass
    logger.info('exit getplanes')


def showplanes(win, lock, run):
    max_distance = 0
    while run['run']:
        time.sleep(.200)
        row = 2
        win.erase()
        Plane.showheader(win)
        # lock.acquire()

        pos_filter = run['pos_filter']
        debug_logging = run['debug_logging']
        for id in sorted(planes, key=planes.__getitem__):
            if planes[id].active and (not pos_filter or planes[id].from_antenna > 0.0):
                if row < rows - 1:
                    planes[id].showincurses(win, row)
                    if planes[id].from_antenna > max_distance:
                        max_distance = planes[id].from_antenna

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
            win.addstr(rows - 1, 1,
                       'Current:{current}  Total (session):{count}  Max (session):{max}  Max Distance:{dist:3.1f}nm  NonPos Filter:{posfilter} DebugLogging:{debug}' \
                       .format(current=str(current), count=str(run['session_count']), max=str(run['session_max']),
                               posfilter=onoff[pos_filter], dist=max_distance, debug=debug_logging))
            win.addstr(rows - 1, cols - 5 - len(now), now)
        except:
            pass

        # lock.release()
        win.refresh()

    logger.info('exit showplanes')


def get_reg_from_regserver(regsvr_url, icao_code):
    url = regsvr_url + '/search?icao_code={icao_code}'.format(icao_code=icao_code)
    logger.info('ask regserver for {} @ {}'.format(icao_code, url))
    reg = ''
    equip = ''
    try:
        logger.info(url)
        r = requests.get(url)
        if r.status_code == 200:
            if 'registration' in r.json():
                reg = r.json()['registration']
                equip = r.json()['equip']
                logger.info('regserver returned: reg:{} type:{}'.format(reg, equip))
    except Exception, ex:
        logger.info('{0}: Failed to get reg from regserver: {1}'.format(str(datetime.now())[:19], ex))

    return reg, equip


def get_registration(id, regsvr_url, reg_cache):
    reg = ''
    instance = 0
    equip = ''

    if id in reg_cache.keys():
        reg = reg_cache[id][0] + '*'
        equip = reg_cache[id][1]
        instance = reg_cache[id][2]
        logger.info('Registration {} instance {} in cache'.format(reg[:-1], instance))
    else:
        registration, equip, = get_reg_from_regserver(regsvr_url, id)
        if registration is not None and len(registration) > 0:
            reg_cache[id] = registration, equip, 0
            instance = 0
            reg = registration + '*'
            logger.info('Reg ' + registration + ' in DB')

    return (reg, equip, instance)


def get_locations(regsvr_url):
    """ Load my recognizeable locations from location table in db """
    url = '{url}/places'.format(url = regsvr_url)
    locations = {}
    try:
        logger.info('Get locations via: {}'.format(url))
        r = requests.get(url)
        if r.status_code == 200:
            for place in r.json():
                data = r.json()[place]
                locations[place] = (data[0], data[1])
    except Exception, ex:
        logger.error('Unable to get places from regserver: {}'.format(ex))

    return locations


def get_planes_of_interest(regsvr_url):
    """ Load my recognizeable planes from plane_of_interest table in db """

    planes = []
    url = '{url}/pois'.format(url = regsvr_url)
    try:
        logger.info('Get planes via: {}'.format(url))
        r = requests.get(url)
        if r.status_code == 200:
            planes = r.json()
    except Exception, ex:
        logger.error('Unable to get planes from regserver: {}'.format(ex))

    return planes



def get_registrations(lock, runstate, regsvr_url):
    locations = get_locations(regsvr_url)
    if len(locations) > 0:
        logger.info('Loaded {} reference locations into cache'.format(len(locations)))
        Plane.locations = locations
        try:
            Plane.antenna_location = locations['antenna']
        except KeyError:
            pass

    planes_of_interest = get_planes_of_interest(regsvr_url)
    if len(planes_of_interest) > 0:
        logger.info('Loaded {} planes of interest into cache'.format(len(planes_of_interest)))
        Plane.planes_of_interest = planes_of_interest

    reg_cache = {}

    while runstate['run']:
        if len(registration_queue) > 0 or len(inactive_queue) > 0:
            logger.debug('RegQ: {} InactiveQ: {}'.format(len(registration_queue), len(inactive_queue)))
        regs = copy.copy(registration_queue)
        for id in regs:
            reg, equip, curr_instance = get_registration(id, regsvr_url, reg_cache)
            reg_cache[id] = (reg, curr_instance)
            lock.acquire()
            planes[id].registration = reg
            planes[id].observe_instance = curr_instance
            planes[id].equip = equip
            registration_queue.remove(id)
            lock.release()

        inactives = copy.copy(inactive_queue)
        for id in inactives:
            instance = planes[id].observe_instance
            lock.acquire()
            inactive_queue.remove(id)
            lock.release()

        time.sleep(.0500)
    logger.info('exit get_registrations')


def main(screen):
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')
    config.read('dump1090curses.local.props')

    dt = str(datetime.now())[:10]

    #logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fname = '{}/{}'.format(config.get('directories', 'log'), config.get('logging','logname'))
    fh = logging.handlers.TimedRotatingFileHandler(fname, when='midnight', interval=1)
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)


    regsvr_url = config.get('regserver', 'base_url')

    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    prev_state = curses.curs_set(0)

    screen.refresh()

    win = curses.newwin(rows, cols, 0, 0)
    win.bkgd(curses.color_pair(1))
    win.box()

    runstate = {'run': True, 'session_count': 0, 'session_max': 0, 'pos_filter': False, 'debug_logging': logger.isEnabledFor(logging.DEBUG)}
    lock = thread.allocate_lock()
    norm_config={'host': config.get('dump1090', 'host'), 'port': int(config.get('dump1090','port')), 'timeout': float(config.get('dump1090', 'timeout')) }
    get_norm = threading.Thread(target=getplanes, args=(lock, runstate, norm_config))
    mlat_config={'host': config.get('dump1090', 'host'), 'port': int(config.get('dump1090','mlat_port')), 'timeout': float(config.get('dump1090', 'timeout')) }
    get_mlat = threading.Thread(target=getplanes, args=(lock, runstate, mlat_config))
    show = threading.Thread(target=showplanes, args=(win, lock, runstate))
    registration = threading.Thread(target=get_registrations, args=(lock, runstate, regsvr_url))
    get_norm.start()
    get_mlat.start()
    show.start()
    registration.start()

    while runstate['run']:
        ch = screen.getch()
        if ch == ord('q'):
            runstate['run'] = False
            logger.debug('kill requested by user')
        elif ch == ord('p'):
            runstate['pos_filter'] = not runstate['pos_filter']
        elif ch == ord('d'):
            if logger.isEnabledFor(logging.DEBUG):
                logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.DEBUG)
            runstate['debug_logging'] = logger.isEnabledFor(logging.DEBUG)

    time.sleep(2)
    curses.curs_set(prev_state)


# usage: radar.py [screen rows]
logger = logging.getLogger(__name__)
if len(sys.argv) > 1:
    rows = int(sys.argv[1]) - 1
try:
    curses.wrapper(main)
except Exception as ex:
    print(ex)
    exit()
