import re
from datetime import datetime
import os
import ConfigParser
import sqlite3

config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
with sqlite3.connect(db_filename) as conn:
    entries = os.listdir('antonakis')
    entries.sort()

    for fl in entries:
        if fl != 'processed':
            with open('antonakis/'+fl) as fd:
                reg = None
                icao_type  = None
                hex_code = None
                for l in fd:
                    x = l.strip()
                    if x.startswith('Reg:'):
                        reg=x.split(' ')[1].strip()
                        #print(reg)
                    elif x.startswith('New Reg:'):
                        reg=x.split(' ')[2].strip()
                    elif x.startswith('ICAO'):
                        icao_type=x.split(' ')[1].strip()
                        ##print(icao_type)
                    elif x.startswith('Hex'):
                        hex_code=x.split(' ')[1].strip()
                        #print(hex_code)
                    elif x.startswith('Status:') and 'Valid Registration' in x and reg is not None and icao_type is not None and hex_code is not None:
                        sql1 = 'update registration set registration="{reg}", equip="{equip}" where icao_code="{icao}";'.format(reg=reg, equip=icao_type, icao=hex_code)
                        sql2 = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}");'\
                                .format(icao=hex_code, reg=reg, dt=str(datetime.now()), equip=icao_type)
                        print(sql1)
                        conn.execute(sql1)
                        print(sql2)
                        conn.execute(sql2)
                        reg = None
                        icao_type  = None
                        hex_code = None
            os.rename('antonakis/'+fl, 'antonakis/processed/'+fl)
