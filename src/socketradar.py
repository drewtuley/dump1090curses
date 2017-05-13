#!/usr/bin/python

import socket
import signal
import time
import sys


if len(sys.argv) > 1:
    o_file = sys.argv[1]
else:
    print('Usage: {0} <output file>'.format(sys.argv[0]))
    exit(1)

with open(o_file, 'w+') as fd:
    signal.signal(signal.SIGINT, signal.default_int_handler)

    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c_socket.connect(('localhost', 30003))
    c_socket.settimeout(1.0)

    while True:
        try:
            buf = c_socket.recv(4096)
            if len(buf) < 1:
                print('Possible buffer underrun - exit')
                break
            fd.write('{0} {1}'.format(time.time(), buf.strip()))
        except KeyboardInterrupt:
            exit(1)
        except Exception as ex:
            print('Exception {}'.format(ex))
            pass
    c_socket.close()
    fd.close()
