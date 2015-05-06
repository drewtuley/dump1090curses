#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 15:17:29$"

import sqlite3
import os
import shelve
import sys
from datetime import datetime

if __name__ == "__main__":
    db_filename = 'data/sqlite_planes.db'
    schema_filename = 'data/RegDBSetup.sql'
        
    db_is_new = not os.path.exists(db_filename)

    with sqlite3.connect(db_filename) as conn:
        if db_is_new:
            print 'Creating schema'
            with open(schema_filename, 'rt') as f:
                schema = f.read()
            conn.executescript(schema)
        crs = conn.cursor()
        
        print 'Updating data from shelf db'
        db = shelve.open('data/shelve_planes.db')

        try:
            if db.has_key('callsigns'):
                cs = db['callsigns']
                for k in cs:
                    # check if exists
                    crs.execute('select * from registration where icao_code = "'+k+'"')
                    data = crs.fetchall()
                    if len(data) == 0:
                        sql='select "'+k+'","'+cs[k]+'","'+str(datetime.now())+'"'
                        print sql
                        conn.execute('insert into registration '+sql)
        except:
            e = sys.exc_info()[0]
            print 'failed to read callsigns cos of '+str(e)
        db.close()
            