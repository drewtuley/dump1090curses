import ConfigParser
import logging
import sqlite3
import sys
from datetime import datetime

import requests
import urllib3.contrib.pyopenssl

if __name__ == "__main__":
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')
    radar24_url = config.get('fr24', 'api')

    urllib3.contrib.pyopenssl.inject_into_urllib3()
    dt = str(datetime.now())[:10]
    logging.basicConfig(format='%(asctime)s %(message)s', filename='log' + '/' + 'logname' + dt + '.log',
                        level=logging.DEBUG)
    logging.captureWarnings(True)

    db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
    if len(sys.argv) >= 2:
        update_filename = sys.argv[1]

        with sqlite3.connect(db_filename) as conn:
            print 'Updating Registrations from : ' + update_filename
            with open(update_filename, 'rt') as f:
                for line in f:
                    icao = line.strip()
                    geturl = radar24_url.format(str(icao))
                    logging.debug('lookup ' + str(icao) + ' on FR24 via:' + geturl)
                    response = requests.get(geturl)
                    json = response.json()
                    logging.debug(json)
                    if 'results' in json:
                        try:
                            reg = json['results'][0]['id']
                            logging.debug('{}={}'.format(str(icao), reg))

                            print ('Adding reg:' + icao)
                            sql = 'insert into registration select "{}","{}","{}" where not exists (select * from registration where icao_code="{}")'.format(
                                icao, reg, str(datetime.now()), icao)
                            print (sql)
                            conn.execute(sql)
                        except:
                            print ('Unable to fetch reg info for ICAO code ' + icao)
                            pass
                    else:
                        print ('Unable to fetch reg info for ICAO code ' + icao)

            conn.commit()
