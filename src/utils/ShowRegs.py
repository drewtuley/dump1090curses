#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$07-May-2015 09:11:32$"

import sqlite3

if __name__ == "__main__":
    conn = sqlite3.connect('data/sqlite_planes.db')
    
    crs = conn.cursor()
    
    crs.execute('select * from registration')
    idx = 1
    for row in crs.fetchall():
        icao, reg, dt = row
        print idx, icao, reg, dt
        idx += 1
        
    conn.close()
