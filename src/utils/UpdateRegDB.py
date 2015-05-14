#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 15:17:29$"

import sqlite3


if __name__ == "__main__":
    db_filename = 'data/sqlite_planes.db'
    schema_filename = 'src/utils/RegDBSetup.sql'
        

    with sqlite3.connect(db_filename) as conn:      
        print 'Creating/Updating schema'
        with open(schema_filename, 'rt') as f:
            schema = f.read()
            conn.executescript(schema)
        
        conn.commit()
        
        conn.close()
            