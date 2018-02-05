import ConfigParser
import logging
import os
import sqlite3
from datetime import datetime

config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

dt = str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=config.get('directories', 'log') + '/anto_parse' + dt + '.log',
                    level=logging.DEBUG)
logging.captureWarnings(True)

db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
with sqlite3.connect(db_filename) as conn:
    entries = os.listdir('antonakis')
    entries.sort()

    for fl in entries:
        if fl != 'processed':
            logging.info('Processing {}'.format(fl))
            with open('antonakis/' + fl) as fd:
                reg = None
                icao_type = None
                hex_code = None
                for l in fd:
                    x = l.strip()
                    if x.startswith('Reg:'):
                        reg = x.split(' ')[1].strip()
                    elif x.startswith('New Reg:'):
                        reg = x.split(' ')[2].strip()
                    elif x.startswith('ICAO'):
                        icao_type = x.split(' ')[1].strip()
                    elif x.startswith('Hex'):
                        hex_code = x.split(' ')[1].strip()
                    elif (x.startswith('Status:') or x.startswith(
                            'New Status:')) and 'Valid Registration' in x and reg is not None and icao_type is not None and hex_code is not None:
                        sql1 = 'update registration set registration="{reg}", equip="{equip}" where icao_code="{icao}";'.format(
                            reg=reg, equip=icao_type, icao=hex_code)
                        sql2 = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}");' \
                            .format(icao=hex_code, reg=reg, dt=str(datetime.now()), equip=icao_type)
                        logging.debug(sql1)
                        conn.execute(sql1)
                        logging.debug(sql2)
                        conn.execute(sql2)
                        reg = None
                        icao_type = None
                        hex_code = None
            os.rename('antonakis/' + fl, 'antonakis/processed/' + fl)
