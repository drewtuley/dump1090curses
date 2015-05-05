#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$30-Apr-2015 13:27:11$"
import shelve
import os


CALLSIGNS = 'callsigns'
if __name__ == "__main__":
    dbname = os.getenv('REGDBNAME','plane.db')
    db = shelve.open(dbname)
    
    if db.has_key(CALLSIGNS):
        cs = db[CALLSIGNS]
        for k in cs:
            print (k+'='+cs[k])
