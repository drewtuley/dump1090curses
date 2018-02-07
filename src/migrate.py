from PyRadar import PyRadar
from PyRadar import Location
from PyRadar import PlaneOfInterest
from PyRadar import Registration
import sqlite3
import ConfigParser


if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')
    db_filename = config.get('directories', 'data') + '/' + config.get('database', 'dbname')

    pyradar = PyRadar()
    pyradar.set_config('dump1090curses.props', 'dump1090curses.local.props')
    session = pyradar.get_db_session(echo=True)


    session.query(Location).delete()
    session.query(PlaneOfInterest).delete()
    session.query(Registration).delete()

    with sqlite3.connect(db_filename) as conn:
        cursor = conn.execute('select * from location')
        for name, latitude, longitude, in cursor.fetchall():
            loc = Location()
            loc.parse(name, latitude, longitude)
            session.add(loc)

        session.commit()

        cursor = conn.execute('select * from plane_of_interest')
        for callsign, in cursor.fetchall():
            poi = PlaneOfInterest()
            poi.parse(callsign)
            session.add(poi)

        session.commit()


        cursor = conn.execute('select * from registration')
        for icao_code, registration, created, equip, in cursor.fetchall():
            reg = Registration()
            reg.parse(icao_code, registration, created, equip)
            session.add(reg)

        session.commit()
