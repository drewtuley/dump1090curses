import ConfigParser
import socket

BUFFER_SIZE = 1024

config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((config.get('dump1090_test_server','host'), int(config.get('dump1090_test_server', 'port'))))
s.settimeout(float(config.get('dump1090_test_server', 'timeout')))

while True:
    try:
        data = s.recv(BUFFER_SIZE)
        if len(data) < 1: break
        print ("received data:", data)
    except socket.error, err:
        pass
s.close()
