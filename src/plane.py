from datetime import datetime
import math
import requests
import sys
import os
import shelve

CALLSIGNS = 'callsigns'

class Plane:
    """A simple SBC Plane class"""
    columns = {0:('ICAO', 7), 1:('Callsign', 11), 2:('Squawk', 7), 3:('Alt', 7), 
        4:('VSpeed', 9), 5:('Track', 7), 6:('Speed(kts)', 12), 7:('Lat', 10), 
        8:('Long', 10), 9:('Nearest Location', 30), 10:('Eventdate', 26), 11:('>15s', 6), 
        12:('Reg', 6)}
    # these locations are of interest to me - insert your own - simple 'Name':(digital_lat, digital_long)
    locations = {'LBA':(53.8736961, -1.6732249), 'Leeds':(53.797365, -1.5580089), 
        'Harrogate':(53.9771475, -1.5430934), 'Skipton':(53.9552364, -2.0219937), 
        'Bradford':(53.7470237, -1.728551), 'Sheffield':(53.3957166, -1.4994562), 
        'Hawes':(54.3040185, -2.198943), 'Doncaster':(53.5188469, -1.1200236), 
        'Wakefield':(53.6782581, -1.3712726), 'Manc-EGCC':(53.2114, -2.1630)}
    callsigns = {}
    radar24url = 'http://www.flightradar24.com/data/_ajaxcalls/autocomplete_airplanes.php?&term='
    db = None
    
    def __init__(self, id, now):
        self.id = id
        self.registration = self.get_registration(id)
        if id in Plane.callsigns.keys():
            cachetime = Plane.callsigns[id][1]
            if (datetime.now()-cachetime).total_seconds() > 30 * 60:
                del Plane.callsigns[id]
                self.callsign = '?'
            else:
                self.callsign = Plane.callsigns[id][0] + '*'
        else:
            self.callsign = '?'
        self.altitude = 0
        self.vspeed = 0
        self.squawk = '0'
        self.track = 0
        self.gs = 0
        self.lat = ''
        self.long = ''
        self.nearest = '?'
        self.eventdate = now	
        self.appeardate = now
	
    def get_registration(self, id):
        if Plane.db == None:
            dbname = os.getenv('REGDBNAME', 'plane.db')
            Plane.db = shelve.open(dbname)
        
        if Plane.db.has_key(CALLSIGNS):
            callsigns = Plane.db[CALLSIGNS]
        else:
            callsigns = {}
        
        if id in callsigns.keys():
            reg = callsigns[id]+'*'
        else:
            reg = self.get_registration_from_fr24(id)
            callsigns[id] = reg
            Plane.db[CALLSIGNS] = callsigns
        
        return reg
    
    def get_registration_from_fr24(self, id):
        """ 
        Not sure how long radar24 will keep this REST endpoint exposed 
        But might as well use it while we can
        """
        geturl = Plane.radar24url + str(id)
        try:
            response = requests.get(geturl)
            if response.status_code == 200:
                return response.json()[0]['id']
            else:
                return ''
        except:
            return 'x'

    def __lt__(self, other):
        return self.appeardate < other.appeardate

    def show(self):
        print "Id=%s callsign=%s squawk=%04d alt=%s track=%s gs=%s lat=%s long=%s" % (self.id, self.callsign, int(self.squawk), self.altitude, self.track, self.gs, self.lat, self.long)
        
    @classmethod
    def close_database(cls):
        if Plane.db != None:
            Plane.db.close()
        
    @classmethod
    def showheader(cls,win):
        col = 0
        for id in Plane.columns:
            win.addstr(0, col, Plane.columns[id][0])
            col += Plane.columns[id][1]
	

    def showincurses(self, win, row):
        col = 0
        for idx in Plane.columns:
            if idx == 0:
                win.addstr(row, col, self.id)
            elif idx == 1:
                win.addstr(row, col, self.callsign)
            elif idx == 2:
                win.addstr(row, col, '{0:04d}'.format(int(self.squawk)))
            elif idx == 3:
                win.addstr(row, col, str(self.altitude))
            elif idx == 4:
                win.addstr(row, col, str(self.vspeed))
            elif idx == 5:
                win.addstr(row, col, '{0:03d}'.format(int(self.track)))
            elif idx == 6:
                win.addstr(row, col, '{0:03d}'.format(int(self.gs)))
            elif idx == 7:
                win.addstr(row, col, str(self.lat))
            elif idx == 8:
                win.addstr(row, col, str(self.long))
            elif idx == 9:
                win.addstr(row, col, self.nearest)
            elif idx == 10:
                win.addstr(row, col, str(self.eventdate))
            elif idx == 11:
                if (datetime.now()-self.eventdate).total_seconds() > 15:
                    win.addstr(row, col, ' *')
            elif idx == 12:
                win.addstr(row, col, self.registration)
            col += Plane.columns[idx][1]


    def update(self, parts):
        """
        Update internal representation of each plane based on the contents
        of the update message
        TODO: Would be more efficient to use the message type (parts[1]) to 
        work out which elements are relevant
        """
        can_update_nearest = False
        if len(parts[6]) > 0 and len(parts[7]) > 0:
            self.eventdate = datetime.strptime(parts[6] + " " + parts[7], "%Y/%m/%d %H:%M:%S.%f")
        if len(parts[10]) > 0:
            self.callsign = parts[10]
            Plane.callsigns[self.id] = (self.callsign, datetime.now())
        if len(parts[11]) > 0:
            self.altitude = parts[11]
        if len(parts[12]) > 0:
            self.gs = parts[12]
        if len(parts[13]) > 0:
            self.track = parts[13]
        if len(parts[14]) > 0:
            self.lat = parts[14]
            can_update_nearest = True
        if len(parts[15]) > 0:
            self.long = parts[15]
            can_update_nearest = True
        if len(parts[16]) > 0:
            self.vspeed = parts[16]
        if len(parts[17]) > 0:
            self.squawk = parts[17]

        if can_update_nearest:
            self.update_nearest()

    def update_nearest(self):
        nearest = 400
        for loc in Plane.locations:
            data = Plane.locations[loc]
            distance = distance_on_sphere(float(self.lat), float(self.long), (data[0]), (data[1]))
            if distance < nearest:
                nearest = distance
                br = bearing(data[0], data[1], float(self.lat), float(self.long))
                self.nearest = '{0:3.1f}'.format(distance) + 'nm ' + cardinal(br) + ' ' + loc


def distance_on_sphere(lat1, long1, lat2, long2):
    """
    Courtesy of http://www.johndcook.com/blog/python_longitude_latitude/
    """
    deg_to_rad = math.pi / 180.0

    phi1 = (90.0 - lat1) * deg_to_rad
    phi2 = (90.0 - lat2) * deg_to_rad

    theta1 = long1 * deg_to_rad
    theta2 = long2 * deg_to_rad

    cos = (math.sin(phi1) * math.sin(phi2) * math.cos(theta1-theta2) + math.cos(phi1) * math.cos(phi2))
    arc = math.acos(cos)

    return arc * 3440

def bearing(lat1, long1, lat2, long2):
    """
    Courtesy of http://www.movable-type.co.uk/scripts/latlong.html
    """
    dtor = math.pi / 180.0
    rlat1 = lat1 * dtor
    rlat2 = lat2 * dtor
    rlong1 = long1 * dtor
    rlong2 = long2 * dtor

    y = math.sin(rlong2-rlong1) * math.cos(rlat2)
    x = math.cos(rlat1) * math.sin(rlat2)-math.sin(rlat1) * math.cos(rlat2) * math.cos(rlong2-rlong1)
    b = math.atan2(y, x) / (math.pi / 180.0)
    b = (b + 360.0) % 360.0
    return b


def cardinal(bearing):
    compass = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N']
    return compass[int(bearing + 11) / 22]


if len(sys.argv) > 1 and sys.argv[1] == 'test':
    testplane = Plane('AABBCC', datetime.now())

    # test distance_on_sphere
    leeds = Plane.locations['Leeds']
    plane = (54.82433, -2.12970)

    print '{0:3.2f}'.format(distance_on_sphere(leeds[0], leeds[1], plane[0], plane[1]))
    print bearing(leeds[0], leeds[1], plane[0], plane[1])

    harrogate = Plane.locations['Harrogate']
    print '{0:3.2f}'.format(distance_on_sphere(leeds[0], leeds[1], harrogate[0], harrogate[1]))
    print bearing(leeds[0], leeds[1], harrogate[0], harrogate[1])


    for b in range(0, 360, 5):
        print str(b) + " " + cardinal(b)

    for loc in Plane.locations:
        print loc

    update = ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '53.123456', '-1.5223123', '', '', '', '']
    testplane.update(update)
    print testplane.nearest

    Plane.callsigns['AABBCCDD'] = ('Hellcat', datetime.now())
    update = ['', '', '', '', '', '', '', '', '', '', 'Pussy', '', '', '', '53.123456', '-1.5223123', '', '', '', '']
    testplane2 = Plane('AABBCCDD', datetime.now())
    print testplane2.callsign
    testplane2.update(update)
    print testplane2.callsign

