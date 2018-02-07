import ConfigParser
import logging
import re
import time
from datetime import datetime

import requests
from persistqueue import PDict

config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

dt = str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=config.get('directories', 'log') + '/anto_scrape' + dt + '.log',
                    level=logging.DEBUG)
logging.captureWarnings(True)

base_url = 'http://www.antonakis.co.uk/registers'
register = 'unitedstatesofamerica'
antodir = config.get('directories','data')+'antonakis/'
url = '{0}/{1}/'.format(base_url, register)

antonakis = PDict('data', 'antonakis')
if 'keys' in antonakis:
    keys = antonakis['keys']
else:
    keys = []

logging.info('Holding {0} entries'.format(len(keys)))

r = requests.get(url)
if r.status_code == 200:
    for reg in re.findall('["](?P<reg>[0-9]{8}.txt?)["]', r.text):
        if reg not in keys:
            logging.info('Setting {0} to false'.format(reg))
            antonakis[reg] = False
            keys.append(reg)

keys.sort()
antonakis['keys'] = keys

for f in keys:
    if antonakis[f] is False:
        ofile = '{0}/{1}'.format(antodir, f)
        logging.info('Download {0} into {1}'.format(f, ofile))
        url = '{0}/{1}/{2}'.format(base_url, register, f)
        r = requests.get(url)
        if r.status_code == 200:
            with open(ofile, 'w') as fd:
                try:
                    text = re.sub(r'[\x80-\xff]', '', r.text)
                    fd.writelines(text)
                    fd.flush()
                    antonakis[f] = True
                except TypeError:
                    logging.error('failed to write {0}'.format(ofile))
        else:
            logging.error('Failed to download {0}'.format(url))

        time.sleep(10)
