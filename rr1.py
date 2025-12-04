import logging
import tomllib
from datetime import datetime

import requests


def get_reg_from_regserver(icao_code, regsvr_url):
    url = regsvr_url + "/search?icao_code={icao_code}".format(icao_code=icao_code)
    print("ask regserver for {} @ {}".format(icao_code, url))
    reg = None
    equip = None
    retry = 5
    while retry > 0 and reg is None and equip is None:
        try:
            print(url)
            r = requests.get(url)
            if r.status_code == 200:
                print("regserver returned {}".format(r.json()))
                if "registration" in r.json():
                    json = r.json()
                    reg = json["registration"]
                    equip = json["equip"]
                    observations = json["observation_log"]

                    print("regserver returned: reg:{} type:{}".format(reg, equip))
                else:
                    break
            else:
                logging.error("regserver returned status_code {}".format(r.status_code))
                retry -= 1
        except Exception as ex:
            print(
                "{0}: Failed to get reg from regserver: {1}".format(
                    str(datetime.now())[:19], ex
                )
            )
            retry -= 1

    return reg, equip, observations


if __name__ == "__main__":
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
        regserver_url = config["regserver"]["base_url"]
        r, q, olog = get_reg_from_regserver("4010EA", regserver_url)
        for e in olog:
            dt = datetime.strptime(e, "%Y-%m-%d %H:%M:%S.%f")
            print(dt)
