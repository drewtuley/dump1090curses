#!/usr/bin/python

import socket


c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
c_socket.connect(('localhost', 30003))
c_socket.settimeout(1.0)

while True:
	try:
		buf = c_socket.recv(4096)
		print (buf.strip()+'XX')
	except:
		print('timeout')
		pass
