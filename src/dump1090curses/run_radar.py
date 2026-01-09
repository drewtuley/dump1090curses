#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 09:27:35$"

import tomllib
import os


def main() -> None:
    home = os.getenv("HOME")
    if len(home) > 0:
        dump1090 = home + "/git/dump1090curses"
        if not os.access(dump1090, os.X_OK):
            print("Error: Unable to access dump1090 dir")
            exit(1)

        os.chdir(dump1090)
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)

            data = config["directories"]["data"]
            logdir = config["directories"]["log"]
            db = data + "/" + config["database"]["dbname"]

            if not os.access(data, os.R_OK):
                print("Warning: Unable to access data dir:" + data)
                os.mkdir(data)

            if not os.access(db, os.R_OK):
                try:
                    print("Attempt to create/update db")
                    os.system("src/utils/UpdateRegDB.py")
                except:
                    print("Error: Failed to update/create db")
                    exit(1)

            if not os.access(logdir, os.R_OK):
                os.mkdir(logdir)

            script = "src/dump1090curses/radar.py"
            lines = 23
            with os.popen("tput lines") as fd:
                for line in fd:
                    lines = line.strip()

            print("opening with " + str(lines) + " lines")
            if os.access(script, os.X_OK):
                os.execl(script, "x", lines)
            else:
                print("Error: unable to execute " + script)
                exit(1)


if __name__ == "__main__":
    main()
