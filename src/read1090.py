#!/usr/bin/python

import socket
import time
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='read data from a port')
    parser.add_argument('--host',help='hostname', default='localhost')
    parser.add_argument('--port',help='port', default=30106)
    args=parser.parse_args()

    host = args.host
    port = int(args.port)

    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
    c_socket.connect((host,port));
    while 1:
        time.sleep(5);
        data=c_socket.recv(2048)
        if ( data == 'q' or data == 'Q'):
            c_socket.close();
            break;
        else:
            print (data.decode('utf-8'))
