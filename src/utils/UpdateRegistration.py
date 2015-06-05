#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$05-Jun-2015 15:38:50$"
import sqlite3
import sys

if __name__ == "__main__":
    db_filename = 'data/sqlite_planes.db'
    if len(sys.argv) >= 2:
        update_filename = sys.argv[1]
        

        with sqlite3.connect(db_filename) as conn:      
            print 'Updating Registrations from : '+update_filename
            with open(schema_filename, 'rt') as f:
                for line in f:
                    icao, reg, = line
                    print ('Adding reg:'+reg)

            conn.commit()