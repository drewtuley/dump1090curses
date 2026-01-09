from datetime import datetime
import sys
import re


FORMAT = "%Y-%m-%d %H:%M:%S,%f"
epoch = datetime(1970, 1, 1)

if len(sys.argv) > 1:
    with open(sys.argv[1]) as fd:
        for line in fd:
            if re.match(".*got line:.*", line.strip()):
                dt = line[:23]
                ldt = datetime.strptime(dt, FORMAT)
                print("{} {}".format((ldt - epoch).total_seconds(), line[33:].strip()))
