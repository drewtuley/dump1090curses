import ConfigParser
import logging
import sqlite3
from datetime import datetime


config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

dt = str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=config.get('directories', 'log') + '/dbload' + dt + '.log',
                    level=logging.DEBUG)
logging.captureWarnings(True)


db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
data_file = config.get('directories', 'data') + '/aircraft_db.csv'

with open(data_file) as fd:
    with sqlite3.connect(db_filename) as conn:
        for l in fd:
            p = l.strip().split(',')
            if len(p) >= 3:
                hex_code = p[0].upper()
                reg = p[1].upper()
                icao_type = p[2].upper()
                if hex_code != 'ICAO' and reg != '00000000' and icao_type != '0000':
                    sql = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}");'\
                                            .format(icao=hex_code, reg=reg, dt=str(datetime.now()), equip=icao_type)
                    logging.debug(sql)
                    conn.execute(sql)

