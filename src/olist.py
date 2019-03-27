import ConfigParser
from datetime import datetime


from PyRadar import PyRadar
from PyRadar import Location
from PyRadar import PlaneOfInterest
from PyRadar import Registration
from PyRadar import ObservationDetail


if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('dump1090curses.props')
    config.read('regserver.props')


    pyradar = PyRadar()
    pyradar.set_config('dump1090curses.props', 'dump1090curses.local.props')
    pyradar.set_logger(pyradar.config.get('directories','log') + '/olist.log')

    session = pyradar.get_db_session()
    obvs = session.query(ObservationDetail).filter(ObservationDetail.event_time > '2019-03-20')
    for obv in obvs:
        print(obv)

    
