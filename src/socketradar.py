#!/usr/bin/python

import socket
import signal
import time
import sys
from datetime import datetime


if len(sys.argv) > 1:
    o_file = sys.argv[1]
else:
    print('Usage: {0} <output file>'.format(sys.argv[0]))
    exit(1)

with open(o_file, 'a') as fd:
    signal.signal(signal.SIGINT, signal.default_int_handler)

    while True:
        connected = False
        while not connected:
            try:
                c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                c_socket.connect(('localhost', 30003))
                c_socket.settimeout(1.0)
                connected = True
            except socket.error, ex:
                print('{0}: Failed to connected : {1}'.format(str(datetime.now())[:19], ex))
                time.sleep(1)

        while True:
            try:
                buf = c_socket.recv(4096)
                if len(buf) < 1:
                    print('{0}: Possible buffer underrun - close/reopen'.format(str(datetime.now())[:19]))
                    break
                print('{2}: Writing {0} bytes to {1}'.format(str(len(buf)), o_file, str(datetime.now())[:19]))
                fd.writelines('{0} {1}\n'.format(time.time(), buf.strip()))
                fd.flush()
            except KeyboardInterrupt:
                exit(1)
            except socket.error ,v:
                #print('Exception {0}'.format(v))
                pass
        c_socket.close()
    fd.close()
