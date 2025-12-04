import sys
import sqlite3
import tomllib

if __name__ == "__main__":
    with open ("config.toml", "rb") as f:
        config = tomllib.load(f)

        regs = {}
        db_filename = config['directories']['data']+'/'+config['database']['dbname']
        with sqlite3.connect(db_filename) as conn:
            sql = 'select icao_code, registration from registration;'
            crsr = conn.cursor()
            crsr.execute(sql)
            for row in crsr.fetchall():
                icao, reg = row
                regs[icao] = reg


        if len(sys.argv) > 1:
            curr_icao = None
            with open(sys.argv[1]) as fd:
                for line in fd:
                    ln=line.strip().split(',')
                    if int(ln[1]) == 3:
                        reg='icao-'+ln[4]
                        if reg != curr_icao:
                            curr_icao = reg
                            print('name,latitude,longitude,type')
                        try:
                            reg=regs[ln[4]]
                        except KeyError:
                            pass
                        print('{},{},{},T'.format(reg,ln[14],ln[15]))
