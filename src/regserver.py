import ConfigParser
import json
import sqlite3
from datetime import datetime

import requests
import urllib3.contrib.pyopenssl
from flask import Flask
from flask import request


class RegServer(Flask):
    db_filename = None
    fr24_url = None
    reg_cache = {}

    def set_db(self, filename):
        self.db_filename = filename

    def set_fr24_url(self, url):
        self.fr24_url = url


app = RegServer(__name__)


@app.route('/search', methods=['GET'])
def search():
    search_icao_code = request.args.get('icao_code', '')
    app.logger.info('search for {}'.format(search_icao_code))
    ret = {}
    if len(app.reg_cache) == 0:
        # get all regs      
        app.reg_cache = {}
        app.logger.info('Warming empty cache')
        sql = 'select icao_code, registration, equip from registration;'
        with sqlite3.connect(app.db_filename) as conn:
            cursor = conn.execute(sql)
            for row in cursor.fetchall():
                code, reg, equip, = row
                app.reg_cache[code] = (reg, equip)
        app.logger.info('Loaded {} regs into cache'.format(len(app.reg_cache)))
    if search_icao_code in app.reg_cache:
        reg, equip = app.reg_cache[search_icao_code]
        app.logger.debug('Cache hit for {}={}'.format(search_icao_code, reg))
        ret = {'registration': reg, 'equip': equip}
    else:
        sql = 'select registration, equip from registration where icao_code = "{}";'.format(search_icao_code)
        app.logger.debug('sql = {}'.format(sql))
        with sqlite3.connect(app.db_filename) as conn:
            cursor = conn.execute(sql)
            for row in cursor.fetchall():
                reg,equip, = row
                app.logger.debug('reg={}'.format(reg))
                ret = {'registration': reg, 'equip': equip}
                # update the cache
                app.reg_cache[search_icao_code] = (reg, equip)

            if len(ret) == 0:
                app.logger.debug('not in cache or db')
                geturl = app.fr24_url.format(str(search_icao_code))
                app.logger.debug('get from fr24 via {}'.format(geturl))
                response = requests.get(geturl)
                retjson = response.json()
                app.logger.debug(retjson)
                if 'results' in retjson and len(retjson['results']) > 0:
                    try:
                        reg = retjson['results'][0]['id']
                        equip = None
                        for result in retjson['results']:
                            if 'detail' in result and 'equip' in result['detail']:
                                equip = result['detail']['equip']
                                if equip is not None:
                                    break
                        app.reg_cache[search_icao_code] = (reg, equip)
                        ret = {'registration': reg, 'equip': equip}

                        sql = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}")'.format(
                            icao=str(search_icao_code), reg=reg, dt=str(datetime.now()), equip=equip)
                        app.logger.debug(sql)
                        conn.execute(sql)
                    except Exception, ex:
                        app.logger.debug('unable to update DB for ICAO code {}: {}'.format(search_icao_code, ex))
                        pass

    return json.dumps(ret)


@app.route('/update', methods=['POST'])
def update():
    return json.dumps({'dd': 1213})


if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')
    app.set_db(db_filename)
    fr24_url = config.get('fr24', 'api')
    app.set_fr24_url(fr24_url)
    urllib3.contrib.pyopenssl.inject_into_urllib3()

    app.run(debug=True)
