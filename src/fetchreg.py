#!/usr/bin/python

from datetime import datetime
import logging
import requests
import urllib3.contrib.pyopenssl
import sys

RADAR24URL = 'https://www.flightradar24.com/v1/search/web/find?limit=16&query={}'

urllib3.contrib.pyopenssl.inject_into_urllib3()
dt=str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s', filename='log'+'/'+'logname'+dt+'.log', level=logging.DEBUG)
logging.captureWarnings(True)

print(sys.argv)
if len(sys.argv) > 1:
    id=sys.argv[1]
else:
    id='403d*'
geturl = RADAR24URL.format(str(id))
logging.debug('lookup '+str(id)+' on FR24 via:'+geturl)
response = requests.get(geturl)
json = response.json()
logging.debug(json)
if 'results' in json:
    try:
        print(json['results'][0]['detail']['equip'])
        logging.debug('{}={}'.format(str(id),json['results'][0]['id']))
        logging.debug('insert into registration select "{}", "{}", "{}";'.format(str(id), json['results'][0]['id'], str(datetime.now())))
    except:
        pass
