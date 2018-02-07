import ConfigParser
import logging
import re
import sqlite3
import sys
from datetime import datetime
from datetime import timedelta

import requests

if len(sys.argv) == 2 and sys.argv[1] == 'all':
    end_date = datetime.strptime('20170801', '%Y%m%d')
else:
    end_date = datetime.now() - timedelta(days=1)
run_date = datetime.now() - timedelta(days=1)

config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

dt = str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=config.get('directories', 'log') + '/egpf_scrape' + dt + '.log',
                    level=logging.DEBUG)
logging.captureWarnings(True)

db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
turl = 'http://www.egpf.info/{mon}{year}/{day}.html'

while run_date > end_date:
    mon = run_date.strftime('%b').lower()
    url = turl.format(mon=mon, year=run_date.year, day=run_date.day)
    logging.info(url)
    r = requests.get(url)
    if r.status_code == 200:
        lines = r.text.split('\n')
        icao_codes = []
        with sqlite3.connect(db_filename) as conn:
            for line in lines:
                m = re.match('^[0-9A-F]{6}', line)
                if m is not None:
                    icao_hex = line[0:6]
                    if icao_hex not in icao_codes:
                        icao_codes.append(icao_hex)
                        reg = line[16:24].strip()
                        icao = line[25:29].strip()
                        if reg != '--------' and icao != '----':
                            logging.info('{0} {1} {2}'.format(icao_hex, reg, icao))
                            sql = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}");' \
                                .format(icao=icao_hex, reg=reg, dt=str(datetime.now()), equip=icao)
                            conn.execute(sql)

    run_date = run_date - timedelta(days=1)
