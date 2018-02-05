#!/usr/bin/python

import ConfigParser
import json
import os
import re
from datetime import datetime

import requests

msg_url = 'Seen a new plane: <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] (#{count})'
repeat_msg_url = 'Seen <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] again'
unknown_url = 'unknown <https://www.radarbox24.com/data/mode-s/{icao}|{icao}>'


def get_my_ip(url):
    r = requests.get(url)
    if r.status_code == 200:
        m = re.search('\d+[.]\d+[.]\d+[.]\d+', r.text)
        if m != None:
            return (m.group())


def post_to_slack(msg):
    payload = {"channel": slack_channel,
               "username": slack_user,
               "text": msg, "icon_emoji": ":airplane:"}
    try:
        requests.post(slack_url, json.dumps(payload))
    except Exception, ex:
        print('{0}: Failed to post to slack: {1}'.format(str(datetime.now())[:19], ex))


config = ConfigParser.SafeConfigParser()
config.read('health.props')

slack_url = config.get('slack', 'url')
slack_channel = config.get('slack', 'channel')
slack_user = config.get('slack', 'slack_user')

myip_url = config.get('myip', 'url')

ip = get_my_ip(myip_url)

msg = '{} connected on {}'.format(os.uname()[1], ip)
post_to_slack(msg)
