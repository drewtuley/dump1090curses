#!/usr/bin/python

import socket
import signal
import time

signal.signal(signal.SIGINT, signal.default_int_handler)

c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
c_socket.connect(('localhost', 30003))
c_socket.settimeout(1.0)

while True:
    try:
        buf = c_socket.recv(4096)
        if len(buf) < 1:
            break
        print('{0} {1}'.format(time.time(), buf.strip()))
    except KeyboardInterrupt:
        exit(1)
    except:
        pass
c_socket.close()
