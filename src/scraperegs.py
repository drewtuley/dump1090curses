#!/usr/bin/python

import logging
import sqlite3
import sys
import tomllib
from datetime import datetime

import requests
import urllib3.contrib.pyopenssl

RADAR24URL = "https://api.flightradar24.com/common/v1/search.json?fetchBy=reg&query="


def open_database(config):
    dbname = config["directories"]["data"] + "/" + config["database"]["dbname"]
    logging.info("Opening db " + dbname)
    return sqlite3.connect(dbname)


def close_database(conn):
    logging.info("Closing db")
    sql = (
        'update observation set endtime="'
        + str(datetime.now())
        + '" where endtime is null'
    )
    conn.execute(sql)
    conn.commit()
    conn.close()


def update_registration(reg, id, conn):
    sql = (
        'insert into registration select "'
        + id.upper()
        + '", "'
        + reg.upper()
        + '","'
        + str(datetime.now())
        + '"'
    )
    logging.debug("Update db with:" + sql)
    upd = conn.execute(sql)
    conn.commit()
    logging.debug("update result=" + str(upd.description))


def load_ids(conn):
    ids = []
    sql = "select icao_code from registration"
    logging.debug("select loaded ids with:" + sql)
    cursor = conn.cursor()
    cursor.execute(sql)

    for id in cursor.fetchall():
        ids.append(id[0].upper())

    return ids


if len(sys.argv) > 1:
    start = end = 0
    try:
        start = int(sys.argv[1], 16)
        end = int(sys.argv[2], 16)
    except ValueError:
        pass
    if start != 0 and end != 0:
        print("start:{} end:{}".format(start, end))

        urllib3.contrib.pyopenssl.inject_into_urllib3()
        with open("config.toml") as f:
            config = tomllib.load(f)
            dt = str(datetime.now())[:10]

            logging.basicConfig(
                format="%(asctime)s %(message)s",
                filename=config["directories"]["log"]
                + "/"
                + config["logging"]["scrapelog"]
                + dt
                + ".log",
                level=logging.DEBUG,
            )
            logging.captureWarnings(True)

            conn = open_database(config)
            ids = load_ids(conn)
            logging.debug("loaded {} cached ids".format(len(ids)))

            icao = start
            while icao <= end:
                print("start at {:x}".format(icao))
                id = "{:X}".format(icao)[:-1]
                geturl = RADAR24URL + str(id) + "*"
                logging.debug("lookup " + str(id) + " on FR24 via:" + geturl)
                try:
                    response = requests.get(geturl)
                    # print (response.json()['result'])
                    if response.status_code == 200:
                        try:
                            for data in response.json()["result"]["response"][
                                "aircraft"
                            ]["data"]:
                                reg = data["registration"]
                                hex = data["hex"]
                                if hex.upper() not in ids:
                                    print
                                    "{0},{1}".format(hex, reg)
                                    update_registration(reg, hex, conn)
                        except KeyError:
                            reg = ""
                except:
                    reg = ""
                icao += 16
            close_database(conn)
