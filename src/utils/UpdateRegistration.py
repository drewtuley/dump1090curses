#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$05-Jun-2015 15:38:50$"
import sqlite3
import sys
import tomllib

if __name__ == "__main__":
    with open("config.toml", "r") as f:
        config = tomllib.load(f)

        db_filename = config["directories"]["data"] + "/" + config["database"]["dbname"]
        if len(sys.argv) >= 2:
            update_filename = sys.argv[1]

            with sqlite3.connect(db_filename) as conn:
                print("Updating Registrations from : " + update_filename)
                with open(update_filename, "rt") as f:
                    for line in f:
                        icao, reg = line.strip().split(",")
                        print("Adding reg:" + reg)
                        sql = (
                            'insert into registration select "'
                            + icao
                            + '","'
                            + reg
                            + '",datetime() where not exists (select * from registration where icao_code="'
                            + icao
                            + '")'
                        )
                        print(sql)
                        conn.execute(sql)

                conn.commit()
