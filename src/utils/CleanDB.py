#!/usr/bin/python

import sqlite3

conn = sqlite3.connect("data/sqlite_planes.db")

crs = conn.cursor()

crs.execute(
    'select count(*) as deletes from registration where registration = "x" or registration=""'
)
for row in crs.fetchall():
    deletes = row
    if int(deletes[0]) > 0:
        print("Deleting " + int(deletes[0]) + " invalid rows")
        crs.execute(
            'delete from registration where registration = "x" or registration=""'
        )
        conn.commit()
conn.close()
