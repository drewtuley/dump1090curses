import sys
import ConfigParser
import sqlite3
from datetime import datetime



valid_keys = ['reg', 'icao', 'type']
if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')

    keys={}
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = arg.strip().split('=')
            if len(p) == 2 and p[0] in valid_keys:
                keys[p[0]] = p[1].replace('"','').replace('\'','')
    keys['dt'] = str(datetime.now())

    with sqlite3.connect(db_filename) as conn:
        sql = 'insert into registration select "{icao}","{reg}","{dt}","{type}" where not exists (select 1 from registration where icao_code="{icao}");'.format(**keys)
        #print(sql)
        conn.execute(sql)
        conn.commit()
