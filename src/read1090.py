#!/usr/bin/python

import socket
import time
import sys

port = 30005
if len(sys.argv) > 1:
    port = int(sys.argv[1])
c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
c_socket.connect(('localhost',port));
while 1:
	time.sleep(5);
	data=c_socket.recv(2048)
	if ( data == 'q' or data == 'Q'):
		c_socket.close();
		break;
	else:
		print data
