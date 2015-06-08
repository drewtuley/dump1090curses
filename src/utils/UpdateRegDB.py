#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 15:17:29$"

import sqlite3
import ConfigParser


if __name__ == "__main__":
    config=ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')
    
    db_filename = config.get('directories','data')+'/'+config.get('database','dbname')
    schema_filename = 'src/utils/RegDBSetup.sql'
        

    with sqlite3.connect(db_filename) as conn:      
        print 'Creating/Updating schema: '+schema_filename
        with open(schema_filename, 'rt') as f:
            schema = f.read()
            conn.executescript(schema)
        
        conn.commit()
