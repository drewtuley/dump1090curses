from nose.tools import *
from src.plane import Plane
from datetime import datetime

def test_plane():
	now=datetime.now()	
	icao="AABBCCDD"
	p = Plane(icao,now)

	assert_equals(len(p.planes_of_interest),7)

