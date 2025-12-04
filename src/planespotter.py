#!/usr/bin/python

import json
import logging.handlers
import os
import re
import socket
import sys
import time
import tomllib
from datetime import datetime

import requests
from expiringdict import ExpiringDict

from plane import Plane
from plane import cardinal

msg_url = "Seen a new plane: <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] (#{count})"
repeat_msg_url = (
    "Seen <https://www.radarbox24.com/data/mode-s/{icao}|{reg}> [{equip}] again"
)
unknown_url = "unknown <https://www.radarbox24.com/data/mode-s/{icao}|{icao}>"


class SpottedPlane(Plane):
    def __init__(self, id, now):
        Plane.__init__(self, id, now)
        self.slacked = {"track": False, "alt": False, "gs": False, "nearest": False}

    def has_track(self):
        return self.track is not None and self.track != 0

    def has_alt(self):
        return self.altitude is not None and self.altitude != 0

    def has_gs(self):
        return self.gs is not None and self.gs != 0

    def has_nearest(self):
        return self.nearest != "?"

    def get_track(self, fmt=" tracking {t} ({o})"):
        return fmt.format(t=self.track, o=cardinal(self.track))

    def get_alt(self, fmt=" at {a}'"):
        return fmt.format(a=self.altitude)

    def get_gs(self, fmt=" ground speed {g} kts"):
        return fmt.format(g=self.gs)

    def can_slack(self):
        return (
            (self.slacked["track"] is False and self.has_track())
            or (
                self.slacked["alt"] is False
                and self.has_alt()
                and self.slacked["gs"] is False
                and self.has_gs()
            )
            or (self.slacked["nearest"] is False and self.has_nearest())
        )

    def slack_msg(self):
        slack_msg = "{r} {e}".format(r=self.registration, e=self.equip)

        if self.slacked["track"] is False and self.has_track():
            slack_msg += self.get_track()
            self.slacked["track"] = True

        if self.slacked["alt"] is False and self.has_alt():
            slack_msg += self.get_alt()
            self.slacked["alt"] = True

        if self.slacked["gs"] is False and self.has_gs():
            slack_msg += self.get_gs()
            self.slacked["gs"] = True

        if self.slacked["nearest"] is False and self.has_nearest():
            slack_msg += " " + self.nearest
            self.slacked["nearest"] = True

        return slack_msg


def get_reg_from_regserver(icao_code):
    url = regsvr_url + "/search?icao_code={icao_code}".format(icao_code=icao_code)
    logger.info("ask regserver for {} @ {}".format(icao_code, url))
    reg = None
    equip = None
    retry = 5
    while retry > 0 and reg is None and equip is None:
        try:
            logger.info(url)
            r = requests.get(url)
            if r.status_code == 200:
                logger.info("regserver returned {}".format(r.json()))
                if "registration" in r.json():
                    reg = r.json()["registration"]
                    equip = r.json()["equip"]
                    logger.info("regserver returned: reg:{} type:{}".format(reg, equip))
                else:
                    break
            else:
                logger.error("regserver returned status_code {}".format(r.status_code))
                retry -= 1
        except Exception as ex:
            logger.info(
                "{0}: Failed to get reg from regserver: {1}".format(
                    str(datetime.now())[:19], ex
                )
            )
            retry -= 1

    return reg, equip


def get_my_ip(url):
    r = requests.get(url)
    if r.status_code == 200:
        m = re.search("\d+[.]\d+[.]\d+[.]\d+", r.text)
        if m is not None:
            return m.group()


def post_to_slack(msg):
    payload = {
        "channel": slack_channel,
        "username": slack_user,
        "text": msg,
        "icon_emoji": ":airplane:",
    }
    try:
        requests.post(slack_url, json.dumps(payload))
    except Exception as ex:
        logger.error(
            "{0}: Failed to post to slack: {1}".format(str(datetime.now())[:19], ex)
        )


def reload_unknowns():
    post_to_slack("reloading any unknown registrations")
    reloads = 0
    still_unknown = []
    for icao in seen_planes:
        reg = seen_planes.get(icao)
        if reg is None:
            reg, equip = get_reg_from_regserver(icao)
            if reg is not None:
                seen_planes[icao] = reg
                reloads += 1
            else:
                still_unknown.append(unknown_url.format(icao=icao))

    post_to_slack("reloaded {0} regs".format(reloads))

    if still_unknown:
        post_to_slack("\n".join(still_unknown))


def is_valid_icao(icao_code):
    if len(icao_code) == 6:
        return re.match("[0-9A-F]{6}", icao_code.upper()) is not None
    else:
        return False


if len(sys.argv) == 1:
    o_file_base = None
else:
    o_file_base = sys.argv[1]

recently_seen = ExpiringDict(max_len=1000, max_age_seconds=3600)
recheck_unknowns = ExpiringDict(max_len=1, max_age_seconds=3600)
seen_planes = {}

with open("config.toml", "rb") as f:
    config = tomllib.load(f)

    dump1090_host = config["dump1090"]["host"]
    dump1090_port = int(config["dump1090"]["port"])
    dump1090_timeout = float(config["dump1090"]["timeout"])

    slack_url = config["slack"]["url"]
    slack_channel = config["slack"]["channel"]
    slack_user = config["slack"]["slack_user"]

    regsvr_url = config["regserver"]["base_url"]
    myip_url = config["myip"]["url"]

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fname = "{}/{}".format(
        config["directories"]["log"], config["logging"]["planespotter"]
    )
    fh = logging.handlers.TimedRotatingFileHandler(fname, when="midnight", interval=1)
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    prev_connected = False

    recheck_unknowns["wait"] = True
    logger.info("Planespotter connected to {}:{}".format(dump1090_host, dump1090_port))
    while True:
        connected = False
        while not connected:
            try:
                c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                c_socket.connect((dump1090_host, dump1090_port))
                c_socket.settimeout(dump1090_timeout)
                connected = True
            except socket.error as ex:
                logger.error(
                    "{0}: Failed to connect : {1}".format(str(datetime.now())[:19], ex)
                )
                time.sleep(1)
        if prev_connected:
            repeat = "(re)"
        else:
            repeat = ""
        myip = get_my_ip(myip_url)
        post_to_slack(
            "planespotter {0}connected on {1} ({2})".format(repeat, os.uname()[1], myip)
        )

        prev_connected = True
        underrun = ""
        while True:
            if "wait" not in recheck_unknowns:
                reload_unknowns()
                recheck_unknowns["wait"] = True
            try:
                buf = c_socket.recv(16384)
                buf = underrun + buf
                underrun = ""
                if len(buf) < 1:
                    logger.info(
                        "{0}: Possible buffer underrun - close/reopen".format(
                            str(datetime.now())[:19]
                        )
                    )
                    break
                tm_day_mins = (
                    datetime.now().day * 24 * 60
                    + (datetime.now().hour * 60)
                    + (datetime.now().minute)
                )

                for line in buf.strip().split("\n"):
                    parts = [x.strip() for x in line.split(",")]
                    if len(parts) < 22:
                        underrun = line
                        break
                    icao = parts[4]
                    if parts[0] in ("MSG", "MLAT") and parts[4] != "000000":
                        icao = parts[4]
                        logger.info("parts={p}".format(p=parts))
                        if is_valid_icao(icao):
                            if icao not in seen_planes:
                                plane = SpottedPlane(icao, datetime.now())
                                reg, equip = get_reg_from_regserver(icao)
                                if reg is None:
                                    reg = icao
                                plane.registration = reg
                                plane.equip = equip
                                seen_planes[icao] = plane
                                if plane.can_slack():
                                    post_to_slack(
                                        "seen plane: {0}".format(plane.slack_msg())
                                    )
                            else:
                                plane = seen_planes[icao]
                                plane.update(parts)
                                if plane.can_slack():
                                    post_to_slack(
                                        "seen plane: {0}".format(plane.slack_msg())
                                    )
            except KeyboardInterrupt:
                logger.error(
                    "{0}: user reqeusted shutdown".format(str(datetime.now())[:19])
                )
                exit(1)
            except socket.error as v:
                # logger.info('Exception {0}'.format(v))
                pass
        try:
            c_socket.close()
        except socket.error as ex:
            logger.error(
                "{0}: Failed to close socket: {1}".format(str(datetime.now())[:19], ex)
            )
