#!/usr/bin/python

import ConfigParser
import json
import os
import signal
import socket
import sys
import time
from datetime import datetime
import requests
import re
from expiringdict import ExpiringDict



msg_url = 'Seen a new plane: <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] (#{count})'
repeat_msg_url = 'Seen <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] again'


def get_reg_from_regserver(icao_code):
    url = regsvr_url + '/search?icao_code={icao_code}'.format(icao_code=icao_code)
    print('ask regserver for {} @ {}'.format(icao_code, url))
    reg = None
    equip = None
    try:
        print(url)
        r = requests.get(url)
        if r.status_code == 200:
            if 'registration' in r.json():
                reg = r.json()['registration']
                equip = r.json()['equip']
    except Exception, ex:
        print('{0}: Failed to get reg from regserver: {1}'.format(str(datetime.now())[:19], ex))

    return reg, equip


def get_my_ip(url):
    r = requests.get(url)
    if r.status_code == 200:
        m=re.search('\d+[.]\d+[.]\d+[.]\d+', r.text)
        if m != None:
            return (m.group())


def post_to_slack(msg):
    payload = {"channel": "#dump1090",
               "username": "dump1090.listener",
               "text": msg, "icon_emoji": ":airplane:"}
    try:
        requests.post(slack_url, json.dumps(payload))
    except Exception, ex:
        print('{0}: Failed to post to slack: {1}'.format(str(datetime.now())[:19], ex))


def term_handler(signum, frame):
    post_to_slack('user requested shutdown')
    exit(1)


def usr_handler(signum, frame):
    unknowns = False
    for icao in seen_planes:
        reg = seen_planes.get(icao)
        if reg is None:
            unknowns = True
            post_to_slack('Unknown reg for: {}'.format(icao))

    if not unknowns:
        post_to_slack('no unknown regs seen')

    return


def write_line(basefile, line):
    parts = line.split(',')
    if len(parts) == 22:
        dt = parts[6].replace('/', '')
        ofile = '{}_{}.txt'.format(basefile, str(dt))
        with open(ofile, 'a') as fd:
            fd.writelines('{0} {1}\n'.format(time.time(), line))
            fd.flush()


if len(sys.argv) == 1:
    print('Usage: {0} <output file>'.format(sys.argv[0]))
    exit(1)
else:
    o_file_base = sys.argv[1]
    recently_seen = ExpiringDict(max_len=1000, max_age_seconds=3600)
    seen_planes = {}

    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    dump1090_host = config.get('dump1090', 'host')
    dump1090_port = int(config.get('dump1090', 'port'))
    dump1090_timeout = float(config.get('dump1090', 'timeout'))

    slack_url = config.get('slack', 'url')
    regsvr_url = config.get('regserver', 'base_url')
    myip_url = config.get('myip', 'url')

    prev_connected = False
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, term_handler)
    signal.signal(signal.SIGUSR1, usr_handler)

    while True:
        connected = False
        while not connected:
            try:
                c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                c_socket.connect((dump1090_host, dump1090_port))
                c_socket.settimeout(dump1090_timeout)
                connected = True
            except socket.error, ex:
                print('{0}: Failed to connect : {1}'.format(str(datetime.now())[:19], ex))
                time.sleep(1)
        if prev_connected:
            repeat = '(re)'
        else:
            repeat = ''
        myip = get_my_ip(myip_url)
        post_to_slack('socketradar {0}connected on {1} ({2})'.format(repeat, os.uname()[1], myip))

        prev_connected = True
        while True:
            try:
                buf = c_socket.recv(4096)
                if len(buf) < 1:
                    print('{0}: Possible buffer underrun - close/reopen'.format(str(datetime.now())[:19]))
                    break
                print('{2}: Writing {0} bytes to {1}'.format(str(len(buf)), o_file_base, str(datetime.now())[:19]))
                tm_day_mins = datetime.now().day * 24 * 60 + (datetime.now().hour * 60) + (datetime.now().minute)

                for line in buf.strip().split('\n'):
                    write_line(o_file_base, line)
                    parts = line.split(',')
                    if len(parts) > 4:
                        icao = parts[4]
                        if icao != '000000':
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
            except KeyboardInterrupt:
                print('{0}: user reqeusted shutdown'.format(str(datetime.now())[:19]))
                exit(1)
            except socket.error, v:
                # print('Exception {0}'.format(v))
                pass
        try:
            c_socket.close()
        except socket.error, ex:
            print('{0}: Failed to close socket: {1}'.format(str(datetime.now())[:19], ex))
