import socket
import sys
import threading
import time
import tomllib
from datetime import datetime

import thread


def send_data(conn, dump_file):
    last_timecode = None
    with open(dump_file) as fd:
        wait = None
        for line in fd:
            ln = line.strip()
            msgparts = ln.split(",")
            parts = msgparts[0].split(" ")
            timecode = float(parts[0])
            msgparts[0] = parts[1]

            if last_timecode:
                wait = (timecode - last_timecode) * 0.1

            last_timecode = timecode

            if str(msgparts[4]) != "000000" and wait:
                time.sleep(wait)
            # replace parts[6] & parts[7] with current time.....
            msgparts[6] = datetime.now().strftime("%Y/%m/%d")
            msgparts[7] = datetime.now().strftime("%H:%M:%S.%f")
            data = ",".join(msgparts) + "\n"
            print("send data: {}".format(data))
            conn.send(data)  # echo

        conn.close()


if len(sys.argv) > 1:
    dump_file = sys.argv[1]
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(
            (
                config["dump1090_test_server"]["host"],
                int(config["dump1090_test_server"]["port"]),
            )
        )
        s.listen(1)

        while True:
            conn, address = s.accept()
            print("Connection address:", address)
            server = threading.Thread(target=send_data, args=(conn, dump_file))
            server.start()
else:
    print("Usage: {} <dump data file>".format(sys.argv[0]))
