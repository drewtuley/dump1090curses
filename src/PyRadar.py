from sqlalchemy import Column, Integer, String, Float, DateTime, Sequence
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import ConfigParser
from datetime import datetime
import json
import logging
import logging.handlers


Base = declarative_base()


class Registration(Base):
    __tablename__ = 'registration'

    icao_code = Column(String, primary_key = True)
    registration = Column(String, index=True)
    equip = Column(String)
    created = Column(DateTime)

    def parse(self, icao_code, registration, created, equip):
        self.icao_code = icao_code
        self.registration = registration
        if created is not None:
            self.created = datetime.strptime(created, '%Y-%m-%d %H:%M:%S.%f')
        else:
            self.created = datetime.now()
        self.equip = equip

    def __repr__(self):
        return 'ICAO: {i} Reg: {r} Type: {e}'.format(i=self.icao_code, r=self.registration, e=self.equip)


class Location(Base):
    __tablename__ = 'location'

    name = Column(String, primary_key = True)
    latitude = Column(Float)
    longitude = Column(Float)

    def parse(self, name, latitude, longitude):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude


class PlaneOfInterest(Base):
    __tablename__ = 'plane_of_interest'

    callsign = Column(String, primary_key = True)

    def parse(self, callsign):
        self.callsign = callsign

    def __repr__(self):
        return json.dumps(self.callsign)


class PyRadar:
    def __init__(self, **kwargs):
        self.config = None
        self.session = None
        self.database = None
        self.session = None
        self.logger = None


    def set_logger(self, filename):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.handlers.TimedRotatingFileHandler(filename, when='midnight', interval=1)
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)


    def set_config(self, *config_files):
        self.config = ConfigParser.SafeConfigParser()
        for file in config_files:
            self.config.read(file)

        try:
            self.database = 'sqlite:///{dir}/{db}'.format(dir=self.config.get('directories', 'data'), db=self.config.get('database', 'dbname'))
    
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as var:
            print(var)

    def get_db_session(self, echo=False):
        if self.session is not None:
            return self.session
        else:
            engine = create_engine(self.database, echo=echo)
            Base.metadata.create_all(engine)

            Session = sessionmaker(bind=engine)
            self.session = Session()
            return self.session


if __name__ == '__main__':
    print('Test')
    pyradar = PyRadar()
    pyradar.set_config('dump1090curses.props', 'dump1090curses.local.props')

    session = pyradar.get_db_session(echo=True)

    reg = Registration()
    reg.parse('112233','BLAH',datetime.now(), 'ALL')
    session.add(reg)


    loc = Location()
    loc.parse('here',1.1,-1.1)
    session.add(loc)

    poi = PlaneOfInterest()
    poi.parse('G-OBMS')
    session.add(poi)

    session.commit()
