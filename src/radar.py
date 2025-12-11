#!/usr/bin/python

## message format from dump1090:30003 as..
# MSG,8,111,11111,405B77,111111,2015/04/15,08:19:34.893,2015/04/15,08:19:34.886,,,,,,,,,,,,0
# MSG,7,111,11111,405B77,111111,2015/04/15,08:19:35.154,2015/04/15,08:19:35.148,,24000,,,,,,,,,,0
# MSG,6,111,11111,405B77,111111,2015/04/15,08:19:35.255,2015/04/15,08:19:35.218,BEE8WQ  ,,,,,,,7634,0,0,0,0
# MSG,5,111,11111,40649F,111111,2015/04/15,08:19:35.612,2015/04/15,08:19:35.606,,25700,,,,,,,0,,0,0
# MSG,7,111,11111,40649F,111111,2015/04/15,08:19:35.880,2015/04/15,08:19:35.869,,25725,,,,,,,,,,0


import tomllib
import copy
import curses
import logging
import logging.handlers
import socket
import sys
import threading
import time
from datetime import datetime

import requests

from plane import Plane

planes = {}
registration_queue = []
onoff = {True: "On", False: "Off"}

COLS: int = 155
ROWS: int = 28


def getplanes(lock, run, config):
    connected = False
    underrun = ""
    logger.info("Connecting with config: {}".format(config))
    while run["run"]:
        try:
            while not connected and run["run"]:
                try:
                    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    c_socket.connect((config["host"], config["port"]))
                    c_socket.settimeout(config["timeout"])
                    connected = True
                except socket.error as err:
                    logger.debug("Failed to connect - err {}".format(err))
                    time.sleep(1.0)
            # logger.info("connected")
            r_lines = c_socket.recv(32768)
            # logger.debug(f"rawdata={r_lines}")
            lines = underrun + r_lines.decode("utf-8")
            # logger.debug(f"decoded={lines}")
            underrun = ""
            if len(lines) < 1:
                connected = False
                c_socket.close()
                break
            for line in lines.strip().split("\n"):
                logger.debug("got line:" + line.strip())
                parts = [x.strip() for x in line.split(",")]
                if len(parts) < 22:
                    underrun = line
                    break
                if parts[0] in ("MSG", "MLAT") and parts[4] != "000000":
                    id = parts[4]
                    with lock:
                        plane = None
                        # logger.debug(f"have got {len(planes)} planes")
                        try:
                            if id in planes:
                                # logger.debug("already have that plane")
                                plane = planes[id]
                            else:
                                # logger.debug(f"adding new plane:{id} - {plane}")
                                plane = Plane(id, datetime.now())
                                registration_queue.append(id)
                                run["session_count"] += 1
                                planes[id] = plane
                        except Exception as ex:
                            logger.error(f"oops: {ex}")
                        if plane is not None:
                            plane.update(parts)
                        else:
                            logger.debug("plane doesnt exist for some reason")
                        removeplanes()
                elif parts[0] == "MSG" and parts[4] == "000000" and int(parts[1]) == 7:
                    with lock:
                        # grungy way to clear all planes
                        logger.info("Clear all active queue")
                elif parts[0] == "STA":
                    id = parts[4]
                    status = parts[10]
                    if status == "RM":
                        plane = planes[id]
                        plane.active = False
                        logger.info(
                            "set id: " + id + " inactive due to dump1090 remove"
                        )

        except:
            pass
    logger.info("exit getplanes")


def showplanes(win, lock, run):
    max_distance = 0
    while run["run"]:
        time.sleep(0.500)
        row = 2
        win.erase()
        Plane.showheader(win)
        # lock.acquire()
        with lock:
            pos_filter = run["pos_filter"]
            debug_logging = run["debug_logging"]
            # logger.debug(f"There are {len(planes)} planes in the list")

            stale_planes = []
            for id in sorted(planes, key=planes.__getitem__):
                this_plane = planes[id]
                stale = (datetime.now() - this_plane.eventdate).total_seconds() > 30
                if stale:
                    stale_planes.append(id)
                if (
                    this_plane.active
                    and (not pos_filter or this_plane.dist_from_antenna > 0.0)
                    and not stale
                ):
                    if row < ROWS - 1:
                        this_plane.showincurses(win, row)
                        if this_plane.dist_from_antenna > max_distance:
                            max_distance = this_plane.dist_from_antenna

                        row += 1
                    else:
                        break

            # logger.debug(f"I have {len(stale_planes)} stale planes")
            for id in stale_planes:
                planes.pop(id, None)

            now = str(datetime.now())[:19]
            current = 0
            for id in planes:
                if planes[id].active:
                    current += 1

            if current > run["session_max"]:
                run["session_max"] = len(planes)

            try:
                win.addstr(
                    ROWS - 1,
                    1,
                    "Current:{current}  Total (session):{count}  Max (session):{max}  Max Distance:{dist:3.1f}nm  NonPos Filter:{posfilter} DebugLogging:{debug}".format(
                        current=str(current),
                        count=str(run["session_count"]),
                        max=str(run["session_max"]),
                        posfilter=onoff[pos_filter],
                        dist=max_distance,
                        debug=debug_logging,
                    ),
                )
                win.addstr(ROWS - 1, COLS - 5 - len(now), now)
            except:
                pass

            # lock.release()
            win.refresh()

    logger.info("exit showplanes")


def get_reg_from_regserver(regsvr_url, icao_code):
    url = regsvr_url + "/search?icao_code={icao_code}".format(icao_code=icao_code)
    logger.info("ask regserver for {} @ {}".format(icao_code, url))
    reg = ""
    equip = ""
    try:
        logger.info(url)
        r = requests.get(url)
        if r.status_code == 200:
            if "registration" in r.json():
                reg = r.json()["registration"]
                equip = r.json()["equip"]
                logger.info("regserver returned: reg:{} type:{}".format(reg, equip))
    except Exception as ex:
        logger.info(
            "{0}: Failed to get reg from regserver: {1}".format(
                str(datetime.now())[:19], ex
            )
        )

    return reg, equip


def get_registration(id, regsvr_url, reg_cache):
    reg = ""
    instance = 0
    equip = ""

    if id in reg_cache.keys():
        reg = reg_cache[id][0] + "*"
        equip = reg_cache[id][1]
        instance = reg_cache[id][2]
        logger.info("Registration {} instance {} in cache".format(reg[:-1], instance))
    else:
        (
            registration,
            equip,
        ) = get_reg_from_regserver(regsvr_url, id)
        if registration is not None and len(registration) > 0:
            reg_cache[id] = registration, equip, 0
            instance = 0
            reg = registration + "*"
            logger.info("Reg " + registration + " in DB")

    return (reg, equip, instance)


def get_locations(regsvr_url):
    """Load my recognizeable locations from location table in db"""
    url = "{url}/places".format(url=regsvr_url)
    locations = {}
    try:
        logger.info("Get locations via: {}".format(url))
        r = requests.get(url)
        if r.status_code == 200:
            for place in r.json():
                data = r.json()[place]
                locations[place] = (data[0], data[1])
    except Exception as ex:
        logger.error("Unable to get places from regserver: {}".format(ex))

    return locations


def get_planes_of_interest(regsvr_url):
    """Load my recognizeable planes from plane_of_interest table in db"""

    poi_planes = []
    url = "{url}/pois".format(url=regsvr_url)
    try:
        logger.info("Get planes via: {}".format(url))
        r = requests.get(url)
        if r.status_code == 200:
            poi_planes = r.json()
    except Exception as ex:
        logger.error("Unable to get planes from regserver: {}".format(ex))

    return poi_planes


def get_registrations(lock, runstate, regsvr_url):

    locations = get_locations(regsvr_url)
    logger.info(f"Regs={locations}")
    if len(locations) > 0:
        logger.info("Loaded {} reference locations into cache".format(len(locations)))
        Plane.locations = locations
        try:
            Plane.antenna_location = locations["antenna"]
        except KeyError:
            pass

    logger.info("get POIS")
    planes_of_interest = get_planes_of_interest(regsvr_url)
    if len(planes_of_interest) > 0:
        logger.info(
            "Loaded {} planes of interest into cache".format(len(planes_of_interest))
        )
        Plane.planes_of_interest = planes_of_interest

    reg_cache = {}
    logger.info("Start reg server proper")
    while runstate["run"]:
        if len(registration_queue) > 0:
            logger.debug("RegQ: {}".format(len(registration_queue)))
        regs = copy.copy(registration_queue)
        for id in regs:
            reg, equip, curr_instance = get_registration(id, regsvr_url, reg_cache)
            reg_cache[id] = (reg, curr_instance)
            with lock:
                planes[id].registration = reg
                planes[id].observe_instance = curr_instance
                planes[id].equip = equip
                registration_queue.remove(id)

        time.sleep(0.0500)
    logger.info("exit get_registrations")


def main(screen):
    with open("config.toml", "rb") as fd:
        config = tomllib.load(fd)

        logger.setLevel(logging.DEBUG)
        fname = "{}/{}".format(
            config["directories"]["log"], config["logging"]["logname"]
        )
        fh = logging.handlers.TimedRotatingFileHandler(
            fname, when="midnight", interval=1
        )
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(funcName)s] %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        regsvr_url = config["regserver"]["base_url"]

        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        prev_state = curses.curs_set(0)

        screen.refresh()

        win = curses.newwin(ROWS, COLS, 0, 0)
        win.bkgd(curses.color_pair(1))
        win.box()

        runstate = {
            "run": True,
            "session_count": 0,
            "session_max": 0,
            "pos_filter": False,
            "debug_logging": logger.isEnabledFor(logging.DEBUG),
        }
        lock = threading.Lock()
        norm_config = {
            "host": config["dump1090"]["host"],
            "port": int(config["dump1090"]["port"]),
            "timeout": float(config["dump1090"]["timeout"]),
        }
        get_norm = threading.Thread(
            target=getplanes, args=(lock, runstate, norm_config)
        )

        show = threading.Thread(target=showplanes, args=(win, lock, runstate))
        registration = threading.Thread(
            target=get_registrations, args=(lock, runstate, regsvr_url)
        )
        get_norm.start()
        show.start()
        registration.start()

        while runstate["run"]:
            ch = screen.getch()
            if ch == ord("q"):
                runstate["run"] = False
                logger.info("kill requested by user")
            elif ch == ord("p"):
                runstate["pos_filter"] = not runstate["pos_filter"]
            elif ch == ord("d"):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.setLevel(logging.INFO)
                else:
                    logger.setLevel(logging.DEBUG)
                runstate["debug_logging"] = logger.isEnabledFor(logging.DEBUG)

        time.sleep(2)
        curses.curs_set(prev_state)


# usage: radar.py [screen rows]
logger = logging.getLogger(__name__)
if len(sys.argv) > 1:
    ROWS = int(sys.argv[1]) - 1
try:
    curses.wrapper(main)
except Exception as ex:
    print(ex)
    exit()
