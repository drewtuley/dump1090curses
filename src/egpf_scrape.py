import re
import sys
from datetime import datetime
from datetime import timedelta
from PyRadar import PyRadar
from PyRadar import Registration

import requests

if len(sys.argv) == 2 and sys.argv[1] == 'all':
    end_date = datetime.strptime('20191201', '%Y%m%d')
else:
    end_date = datetime.now() - timedelta(days=1)
run_date = datetime.now() - timedelta(days=1)

pyradar = PyRadar()
pyradar.set_config('dump1090curses.props','dump1090curses.local.props')
logdir = pyradar.config.get('directories', 'log')
pyradar.set_logger(logdir+'/egpf_scrape.log')

pyradar.logger.info('EGPF Scrape: {} -> {}'.format(run_date,end_date))

turl = 'http://www.egpf.info/{mon}{year}/{day}.html'

session = pyradar.get_db_session()
while run_date > end_date:
    mon = run_date.strftime('%b').lower()
    url = turl.format(mon=mon, year=run_date.year, day=run_date.day)
    pyradar.logger.info(url)
    r = requests.get(url)
    if r.status_code == 200:
        lines = r.text.split('\n')
        icao_codes = []
        for line in lines:
            m = re.match('^[0-9A-F]{6}', line)
            if m is not None:
                icao_hex = line[0:6]
                if icao_hex not in icao_codes:
                    icao_codes.append(icao_hex)
                    reg = line[16:24].strip()
                    icao = line[25:29].strip()
                    if reg != '--------' and icao != '----':
                        exists = session.query(Registration).filter_by(icao_code = icao_hex).first()
                        if exists is None:
                            pyradar.logger.info('Adding {0} {1} {2}'.format(icao_hex, reg, icao))
                            newreg = Registration('egpf_scrape')
                            newreg.parse(icao_hex, reg, str(datetime.now()), icao)
                            session.add(newreg)
                            session.commit()

    run_date = run_date - timedelta(days=1)
