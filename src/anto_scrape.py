import requests
import re
import time
from persistqueue import PDict


base_url = 'http://www.antonakis.co.uk/registers'
register = 'unitedstatesofamerica'
dir = 'antonakis'
url = '{0}/{1}/'.format(base_url, register)

antonakis = PDict('data','antonakis')
if 'keys' in antonakis:
    keys = antonakis['keys']
else:
    keys = []

print('Holding {0} entries'.format(len(keys)))

r = requests.get(url)
if r.status_code == 200:
    for reg in re.findall('["](?P<reg>[0-9]{8}.txt?)["]', r.text):
        if reg not in keys:
            print('Setting {0} to false'.format(reg))
            antonakis[reg] = False
            keys.append(reg)

keys.sort()
antonakis['keys'] = keys


for f in keys:
    if antonakis[f] is False:
        ofile='{0}/{1}'.format(dir, f)
        print('Download {0} into {1}'.format(f, ofile))
        url = '{0}/{1}/{2}'.format(base_url, register, f)
        r = requests.get(url)
        if r.status_code == 200:
            with open(ofile, 'w') as fd:
                try:
                    text = re.sub(r'[\x80-\xff]','', r.text)
                    fd.writelines(text)
                    fd.flush()
                    antonakis[f] = True
                except TypeError:
                    print('failed to write {0}'.format(ofile))
        else:
            print('Failed to download {0}'.format(url))

        time.sleep(10)
