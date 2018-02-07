import logging
import os
from datetime import datetime

from PyRadar import PyRadar
from PyRadar import Registration


pyradar = PyRadar()
pyradar.set_config('dump1090curses.props', 'dump1090curses.local.props')

dt = str(datetime.now())[:10]
logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=pyradar.config.get('directories', 'log') + '/anto_parse' + dt + '.log',
                    level=logging.DEBUG)
logging.captureWarnings(True)

antodir = pyradar.config.get('directories', 'data')+'/antonakis/'
session = pyradar.get_db_session() 
entries = os.listdir(antodir)
entries.sort()

for fl in entries:
    if fl != 'processed':
        logging.info('Processing {}'.format(fl))
        with open(antodir + fl) as fd:
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
                    existing = session.query(Registration).filter_by(icao_code = hex_code).first()
                    if existing is not None:
                        logging.info('Update icao: {}'.format(hex_code))
                        session.query(Registration).filter_by(icao_code = hex_code).\
                            update({'registration': reg, 'equip': icao_type}, synchronize_session='evaluate')
                    else:
                        logging.info('Add icao: {} reg: {}'.format(hex_code, reg))
                        new_reg = Registration()
                        new_reg.parse(hex_code, reg, str(datetime.now()), icao_type)
                        session.add(new_reg)
                        session.commit()
                    reg = None
                    icao_type = None
                    hex_code = None
        os.rename(antodir + fl, antodir+'/processed/' + fl)
