#!/usr/bin/python

import json
import os
import signal
import socket
import sys
import time
from datetime import datetime
import ConfigParser

import requests

msg_url = 'Seen a new plane: <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> (#{count})'


def get_reg_from_regserver(icao_code):
    url = regsvr_url.format(icao_code=icao_code)
    reg = None
    try:
        r = requests.get(url)
        if r.status_code == 200:
            if 'registration' in r.json():
                reg = r.json()['registration']
    except Exception, ex:
        print('{0}: Failed to get reg from regserver: {1}'.format(str(datetime.now())[:19], ex))

    return reg


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


if len(sys.argv) == 1:
    print('Usage: {0} <output file>'.format(sys.argv[0]))
    exit(1)
else:
    o_file = sys.argv[1]
    seen_planes = []

    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    dump1090_host = config.get('dump1090','host')
    dump1090_port  = int(config.get('dump1090','port'))
    dump1090_timeout  = float(config.get('dump1090','timeout'))

    slack_url = config.get('slack','url')
    regsvr_url = config.get('regserver','url')

    with open(o_file, 'a') as fd:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, term_handler)

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

            post_to_slack('socketradar connected on {}'.format(os.uname()[1]))
            while True:
                try:
                    buf = c_socket.recv(4096)
                    if len(buf) < 1:
                        print('{0}: Possible buffer underrun - close/reopen'.format(str(datetime.now())[:19]))
                        break
                    print('{2}: Writing {0} bytes to {1}'.format(str(len(buf)), o_file, str(datetime.now())[:19]))
                    for line in buf.strip().split('\n'):
                        fd.writelines('{0} {1}\n'.format(time.time(), line))
                        parts = line.split(',')
                        if parts[4] != '000000' and parts[4] not in seen_planes:
                            seen_planes.append(parts[4])
                            reg = get_reg_from_regserver(parts[4])
                            post_to_slack(msg_url.format(icao=parts[4], reg=reg, count=len(seen_planes)))
                    fd.flush()
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
