import sqlite3
import tomllib

import requests
import urllib3.contrib.pyopenssl


def update(search_icao_code, conn, fr24url):
    print("search for {}".format(search_icao_code))
    geturl = fr24_url.format(str(search_icao_code))
    print("get from fr24 via {}".format(geturl))
    response = requests.get(geturl)
    retjson = response.json()
    print(retjson)
    if "results" in retjson and len(retjson["results"]) > 0:
        try:
            equip = None
            for result in retjson["results"]:
                print("results={}".format(result))
                if "detail" in result and "equip" in result["detail"]:
                    equip = result["detail"]["equip"]
                    print("equip={}".format(equip))
                    if equip is not None:
                        break
            if equip is not None:
                sql = 'update registration set equip="{equip}" where icao_code="{icao}";'.format(
                    icao=str(search_icao_code), equip=equip
                )
                print(sql)
                conn.execute(sql)
                conn.commit()
            else:
                print("Unable to determine equip")
        except Exception as ex:
            print(
                "unable to update DB for ICAO code {}: {}".format(search_icao_code, ex)
            )
            pass


if __name__ == "__main__":
    with open("config.toml") as f:
        config = tomllib.load(f)

        db_filename = config["directories"]["data"] + "/" + config["database"]["dbname"]
        fr24_url = config.get("fr24", "api")
        urllib3.contrib.pyopenssl.inject_into_urllib3()

        missing_equip = []
        sql = "select icao_code from registration where equip is null;"
        with sqlite3.connect(db_filename) as conn:
            cursor = conn.execute(sql)
            for row in cursor.fetchall():
                (code,) = row
                missing_equip.append(code)
        print("Found {} registrations missing equip values".format(len(missing_equip)))

        for code in missing_equip:
            update(code, conn, fr24_url)
