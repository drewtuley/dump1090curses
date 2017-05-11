#!/usr/bin/python

import socket
import signal
import sys

c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
c_socket.connect(('localhost', 30003))
c_socket.settimeout(1.0)

signal.signal(signal.SIGINT, signal.default_int_handler)
while True:
    try:
        buf = c_socket.recv(4096)
        print(buf.strip())
    except KeyboardInterrupt:
        exit(1)
    except:
        pass
