#!/usr/bin/python

from datetime import datetime
import logging
import requests
import urllib3.contrib.pyopenssl
import sys

RADAR24URL = 'https://api.flightradar24.com/common/v1/search.json?fetchBy=reg&query='

urllib3.contrib.pyopenssl.inject_into_urllib3()
dt=str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s', filename='log'+'/'+'logname'+dt+'.log', level=logging.DEBUG)
logging.captureWarnings(True)

print(sys.argv)
if len(sys.argv) > 1:
    id=sys.argv[1]
else:
    id='403d*'
geturl = RADAR24URL + str(id)
logging.debug('lookup '+str(id)+' on FR24 via:'+geturl)
response = requests.get(geturl)
logging.debug(response.json()['result'])
try:
	response = requests.get(geturl)
	print (response.json()['result'])
	if response.status_code == 200:
		for d in response.json()['result']['response']['aircraft']['data']:
			print d
	else:
		print ''
except:
	print 'x'

