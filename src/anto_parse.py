import re
from datetime import datetime
import sys

for fl in sys.argv[1:]:
    with open(fl) as fd:
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
                sql = None
                sql1 = 'update registration set registration="{reg}", equip="{equip}" where icao_code="{icao}";'.format(reg=reg, equip=icao_type, icao=hex_code)
                sql2 = 'insert into registration select "{icao}","{reg}","{dt}","{equip}" where not exists (select * from registration where icao_code="{icao}");'\
                        .format(icao=hex_code, reg=reg, dt=str(datetime.now()), equip=icao_type)
                sql = '{0}{1}'.format(sql1,sql2) 

                if sql is not None:
                    print(sql)
                    reg = None
                    icao_type  = None
                    hex_code = None


print('.exit')
