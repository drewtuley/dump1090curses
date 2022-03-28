import re
import sys
from datetime import datetime
from PyRadar import PyRadar
from PyRadar import Registration


from xlrd import open_workbook


def dashify(org_reg):
    new_reg = org_reg
    if re.match(r'^[GDIFCM2][A-Z]{4}$', org_reg):
        new_reg='{0}-{1}'.format(org_reg[0],org_reg[1:])
    elif re.match(r'^(OE|OO|UR|HB|EI|LX|HA|TC|PH|ES|EC|T7|OY|9H|SE|LN|SP|LY|YR)[A-Z]{3}$', org_reg):
        new_reg='{0}-{1}'.format(org_reg[0:2],org_reg[2:])
    return new_reg


pyradar = PyRadar()
pyradar.set_config('dump1090curses.props','dump1090curses.local.props')
logdir = pyradar.config.get('directories', 'log')
datadir = pyradar.config.get('directories', 'data')
pyradar.set_logger(logdir+'/eurocontrol_scrape.log')

pyradar.logger.info('EuroControl Scrape:')


session = pyradar.get_db_session()
xls = '{}/euroc.xls'.format(datadir)

pyradar.logger.info('Load XLS from {}'.format(xls))
wb = open_workbook(xls)
if wb.sheet_loaded('export'):
    sht = wb.sheet_by_name('export')
    row = 3
    while row < sht.nrows:
        icao = sht.cell_value(row, 2).strip()
        reg = dashify(sht.cell_value(row, 3).strip())
        icao_hex = sht.cell_value(row, 4).strip()

        exists = session.query(Registration).filter_by(icao_code = icao_hex).first()
        if exists is None:
            pyradar.logger.info('Adding {0} {1} {2}'.format(icao_hex, reg, icao))
            newreg = Registration('eurocontrol_scrape')
            newreg.parse(icao_hex, reg, str(datetime.now()), icao)
            session.add(newreg)
            session.commit()

        row += 1
else:
    pyradar.logger.error('Unable to load sheet "export" from {}'.format(xls))

