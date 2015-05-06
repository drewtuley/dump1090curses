#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 08:49:11$"

import os

if __name__ == "__main__":
    home=os.getenv('HOME')
    if len(home) > 0:
        dump1090=home+'/git/dump1090curses'
        data=dump1090+'/data'
        if not os.access(data, os.R_OK):
            print 'Unable to access data dir:'+data
            exit(1)
        os.environ['REGDBNAME'] = data+'/planes.db'
        script=dump1090+'/src/read_regs.py'
        if os.access(script, os.X_OK):
	    print script
            os.execl(script, data)
        else:
            print 'unable to execute '+script
            exit(1)
