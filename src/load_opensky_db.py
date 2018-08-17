import ConfigParser
import logging
import sqlite3
from datetime import datetime

config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

dt = str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=config.get('directories', 'log') + '/opensky_load' + dt + '.log',
                    level=logging.DEBUG)
logging.captureWarnings(True)

db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
data_file = config.get('directories', 'data') + '/aircraftDatabase.csv'

with open(data_file) as fd:
    with sqlite3.connect(db_filename) as conn:
        for l in fd:
            p = l.strip().replace('"','').split(',')
            if len(p) >= 6:
                hex_code = p[0].upper()
                reg = p[1].upper()
                icao_type = p[5].upper()
                if hex_code != 'ICAO24' and reg != '' and icao_type != '':
                    sql = 'insert into registration select "{icao}","{reg}","{equip}","{dt}" where not exists (select * from registration where icao_code="{icao}");' \
                        .format(icao=hex_code, reg=reg, dt=str(datetime.now()), equip=icao_type)
                    logging.debug(sql)
                    conn.execute(sql)
