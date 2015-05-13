#!/usr/bin/python

import sqlite3

conn = sqlite3.connect('data/sqlite_planes.db')

crs = conn.cursor()

crs.execute('delete from registration where registration = "x" or registration=""')
conn.commit()
