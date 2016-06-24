#!/usr/bin/python

import socket
import time

c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
c_socket.connect(('localhost',30005));
while 1:
	time.sleep(5);
	data=c_socket.recv(2048)
	if ( data == 'q' or data == 'Q'):
		c_socket.close();
		break;
	else:
		print data
