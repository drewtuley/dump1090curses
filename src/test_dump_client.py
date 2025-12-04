import socket
import tomllib

BUFFER_SIZE = 1024

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(
        (
            config["dump1090_test_server"]["host"],
            int(config["dump1090_test_server"]["port"]),
        )
    )
    s.settimeout(float(config["dump1090_test_server"]["timeout"]))

    while True:
        try:
            data = s.recv(BUFFER_SIZE)
            if len(data) < 1:
                break
            print("received data:", data)
        except socket.error as err:
            pass
    s.close()
