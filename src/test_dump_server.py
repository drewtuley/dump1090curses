import ConfigParser
import socket
import time
import thread
import threading

TCP_IP = 'localhost'


def send_data(conn, dump_file):
    last_timecode = None
    with open(dump_file) as fd:
        wait = None
        for line in fd:
            ln = line.strip()
            parts = ln.split(' ')
            timecode = float(parts[0])

            if last_timecode:
                wait = (timecode - last_timecode) * 0.1

            last_timecode = timecode

            if wait:
                time.sleep(wait)

            print("send data:", parts[1:])
            conn.send(','.join(parts[1:]))  # echo

        conn.close()


config = ConfigParser.SafeConfigParser()
config.read('dump1090curses.props')

dump_file = '/Volumes/share/dump1090_20170518.txt'

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, int(config.get('dump1090_test_server', 'port'))))
s.listen(1)

while True:
    conn, address = s.accept()
    print('Connection address:', address)
    server = threading.Thread(target=send_data, args=(conn, dump_file))
    server.start()

