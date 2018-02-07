import ConfigParser
import json
from datetime import datetime

import requests
import urllib3.contrib.pyopenssl
from flask import Flask
from flask import request

from PyRadar import PyRadar
from PyRadar import Location
from PyRadar import PlaneOfInterest
from PyRadar import Registration


class RegServer(Flask):
    fr24_url = None
    reg_cache = {}
    loc_cache = {}
    logger = None

    def set_db(self, filename):
        self.db_filename = filename

    def set_fr24_url(self, url):
        self.fr24_url = url

    def set_pyradar(self, pyradar):
        self.pyradar = pyradar

    def set_logger(self, logger):
        self.logger = logger

app = RegServer(__name__)

@app.route('/places', methods=['GET'])
def places():
    if len(app.loc_cache) == 0:
        app.loc_cache = {}
        session = app.pyradar.get_db_session()
        locs = session.query(Location)
        for loc in locs:
            app.loc_cache[loc.name] = (loc.latitude, loc.longitude)
    return json.dumps(app.loc_cache)


@app.route('/pois', methods=['GET'])
def pois():
    session = app.pyradar.get_db_session()
    pois = session.query(PlaneOfInterest)
    ret = []
    for poi in pois:
        ret.append(poi.callsign)
    return json.dumps(ret)


@app.route('/search', methods=['GET'])
def search():
    search_icao_code = request.args.get('icao_code', '').upper()
    app.logger.info('search for {}'.format(search_icao_code))
    ret = {}
    session = app.pyradar.get_db_session()
    if len(app.reg_cache) == 0:
        # get all regs      
        app.reg_cache = {}
        app.logger.info('Warming empty cache')
        regs = session.query(Registration)
        for reg in regs:
            app.reg_cache[reg.icao_code] = (reg.registration, reg.equip)
        app.logger.info('Loaded {} regs into cache'.format(len(app.reg_cache)))
    if search_icao_code in app.reg_cache:
        reg, equip = app.reg_cache[search_icao_code]
        app.logger.debug('Cache hit for {}={}'.format(search_icao_code, reg))
        ret = {'registration': reg, 'equip': equip}
    else:
        reg = session.query(Registration).filter_by(icao_code = search_icao_code).first()
        print(reg)
        if reg is not None:
            ret = {'registration': reg.registration, 'equip': reg.equip}
            # update the cache
            app.reg_cache[search_icao_code] = (reg.registration, reg.equip)

        else:
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
                    app.logger.debug(ret)
                    new_reg = Registration()
                    new_reg.parse(search_icao_code, reg, str(datetime.now()), equip)
                    app.logger.debug('Add new reg {}'.format(new_reg))
                    session.add(new_reg)
                    session.commit()
                except Exception, ex:
                    app.logger.debug('unable to update DB for ICAO code {}: {}'.format(search_icao_code, ex))
                    pass

    return json.dumps(ret)


if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')

    fr24_url = config.get('fr24', 'api')
    app.set_fr24_url(fr24_url)
    urllib3.contrib.pyopenssl.inject_into_urllib3()

    pyradar = PyRadar()
    pyradar.set_config('dump1090curses.props', 'dump1090curses.local.props')
    pyradar.set_logger(pyradar.config.get('directories','log') + '/regserver.log')
    app.set_pyradar(pyradar)
    app.set_logger(pyradar.logger)


    app.run(debug=True)
