#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 09:27:35$"

import os
import string

if __name__ == "__main__":
    home=os.getenv('HOME')
    if len(home) > 0:
        dump1090=home+'/git/dump1090curses'
        data=dump1090+'/data'
        logdir=dump1090+'/log'
        if not os.access(data, os.R_OK):
            print 'Warning: Unable to access data dir:'+data
            os.mkdir(data)
        
        if not os.access(logdir, os.R_OK):
            os.mkdir(logdir)
            
        os.environ['REGDBNAME'] = data+'/sqlite_planes.db'
        os.environ['LOGDIR'] = logdir
        script=dump1090+'/src/radar.py'
	lines = 23
	with os.popen('tput lines') as fd:
            for line in fd:
		lines = (string.rstrip(line))
	print 'opening with '+str(lines)+' lines'
        if os.access(script, os.X_OK):
            os.execl(dump1090+'/src/radar.py','x',lines)
        else:
            print 'Error: unable to execute '+script
            exit(1)
