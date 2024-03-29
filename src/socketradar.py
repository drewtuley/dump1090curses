#!/usr/bin/python

import configparser
import json
import os
import re
import requests
import socket
import sys
import time
import logging
import logging.handlers
from datetime import datetime
from expiringdict import ExpiringDict

msg_url = 'Seen a new plane: <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] (#{count})'
repeat_msg_url = 'Seen <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] again'
unknown_url = 'unknown <https://www.radarbox24.com/data/mode-s/{icao}|{icao}>'


def get_reg_from_regserver(icao_code):
    url = regsvr_url + '/search?icao_code={icao_code}'.format(icao_code=icao_code)
    logger.info('ask regserver for {} @ {}'.format(icao_code, url))
    reg = None
    equip = None
    retry = 5
    while retry > 0 and reg is None and equip is None:
        try:
            logger.info(url)
            r = requests.get(url)
            if r.status_code == 200:
                logger.info('regserver returned {}'.format(r.json()))
                if 'registration' in r.json():
                    reg = r.json()['registration']
                    equip = r.json()['equip']
                    logger.info('regserver returned: reg:{} type:{}'.format(reg, equip))
                else:
                    break
            else:
                logger.error('regserver returned status_code {}'.format(r.status_code))
                retry -= 1 
        except Exception as ex:
            logger.info('{0}: Failed to get reg from regserver: {1}'.format(str(datetime.now())[:19], ex))
            retry -= 1

    return reg, equip


def get_my_ip(url):
    r = requests.get(url)
    if r.status_code == 200:
        m = re.search('\d+[.]\d+[.]\d+[.]\d+', r.text)
        if m is not None:
            return (m.group())


def post_to_slack(msg):
    payload = {"channel": slack_channel,
               "username": slack_user,
               "text": msg, "icon_emoji": ":airplane:"}
    try:
        requests.post(slack_url, json.dumps(payload))
    except Exception as ex:
        logger.error('{0}: Failed to post to slack: {1}'.format(str(datetime.now())[:19], ex))


def reload_unknowns():
    post_to_slack('reloading any unknown registrations')
    reloads = 0
    still_unknown = []
    for icao in seen_planes:
        reg = seen_planes.get(icao)
        if reg is None:
            reg, equip = get_reg_from_regserver(icao)
            if reg is not None:
                seen_planes[icao] = reg
                reloads += 1
            else:
                still_unknown.append(unknown_url.format(icao=icao))

    post_to_slack('reloaded {0} regs'.format(reloads))

    if still_unknown:
        post_to_slack('\n'.join(still_unknown))


def is_valid_icao(icao_code):
    if len(icao_code) == 6:
        return re.match('[0-9A-F]{6}', icao_code.upper()) is not None
    else:
        return False


def write_line(basefile, line, message_types_to_write):
    if basefile is None:
        return
    parts = line.split(',')
    if len(parts) == 22 and int(parts[1]) in message_types_to_write:
        dt = parts[6].replace('/', '')
        ofile = '{}_{}.txt'.format(basefile, str(dt))
        with open(ofile, 'a') as fd:
            fd.writelines('{0} {1}\n'.format(time.time(), line))
            fd.flush()


if len(sys.argv) == 1:
    o_file_base = None
else:
    o_file_base = sys.argv[1]

recently_seen = ExpiringDict(max_len=1000, max_age_seconds=3600)
recheck_unknowns = ExpiringDict(max_len=1, max_age_seconds=3600)
seen_planes = {}

config = configparser.ConfigParser()
config.read('dump1090curses.props')
config.read('dump1090curses.local.props')

dump1090_host = config.get('dump1090', 'host')
dump1090_port = int(config.get('dump1090', 'port'))
dump1090_timeout = float(config.get('dump1090', 'timeout'))

slack_url = config.get('slack', 'url')
slack_channel = config.get('slack', 'channel')
slack_user = config.get('slack', 'slack_user')

regsvr_url = config.get('regserver', 'base_url')
myip_url = config.get('myip', 'url')

s_types_to_write = config.get('output','types_to_write')
if s_types_to_write is None:
    types_to_write = [1,2,3,4,5,6,7,8]
else:
    types_to_write = eval('['+s_types_to_write+']')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fname = '{}/{}'.format(config.get('directories', 'log'), config.get('logging','socketradar'))
fh = logging.handlers.TimedRotatingFileHandler(fname, when='midnight', interval=1, backupCount=5)
fh.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(fmt)
logger.addHandler(fh)

prev_connected = False

recheck_unknowns['wait'] = True
logger.info('Socketradar connected to {}:{}'.format(dump1090_host, dump1090_port))
while True:
    connected = False
    while not connected:
        try:
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c_socket.connect((dump1090_host, dump1090_port))
            c_socket.settimeout(dump1090_timeout)
            connected = True
        except socket.error as ex:
            logger.error('{0}: Failed to connect : {1}'.format(str(datetime.now())[:19], ex))
            time.sleep(1)
    if prev_connected:
        repeat = '(re)'
    else:
        repeat = ''
    myip = get_my_ip(myip_url)
    post_to_slack('socketradar {0}connected on {1} ({2})'.format(repeat, os.uname()[1], myip))

    prev_connected = True
    while True:
        if 'wait' not in recheck_unknowns:
            reload_unknowns()
            recheck_unknowns['wait'] = True
        try:
            buf = c_socket.recv(16384).decode('utf-8')
            if len(buf) < 1:
                logger.info('{0}: Possible buffer underrun - close/reopen'.format(str(datetime.now())[:19]))
                break
            logger.info('{2}: Writing {0} bytes to {1}'.format(str(len(buf)), o_file_base, str(datetime.now())[:19]))
            tm_day_mins = datetime.now().day * 24 * 60 + (datetime.now().hour * 60) + (datetime.now().minute)

            for line in buf.strip().split('\n'):
                write_line(o_file_base, line, types_to_write)
                parts = line.split(',')
                if len(parts) > 4:
                    icao = parts[4]
                    if icao != '000000' and is_valid_icao(icao):
                        if icao not in seen_planes:
                            reg, equip = get_reg_from_regserver(icao)
                            seen_planes[icao] = reg
                            recently_seen[icao] = reg
                            if reg is None:
                                reg = icao
                            post_to_slack(msg_url.format(icao=icao, reg=reg, equip=equip, count=len(seen_planes)))
                        elif icao not in recently_seen:
                            reg, equip = get_reg_from_regserver(icao)
                            recently_seen[icao] = reg
                            post_to_slack(repeat_msg_url.format(icao=icao, reg=reg, equip=equip))
                    else:
                        logger.error('{0}: invalid ICAO code <{1}>'.format(str(datetime.now())[:19], icao))
        except KeyboardInterrupt:
            logger.error('{0}: user reqeusted shutdown'.format(str(datetime.now())[:19]))
            exit(1)
        except socket.error as v:
            # logger.info('Exception {0}'.format(v))
            pass
    try:
        c_socket.close()
    except socket.error as ex:
        logger.error('{0}: Failed to close socket: {1}'.format(str(datetime.now())[:19], ex))
