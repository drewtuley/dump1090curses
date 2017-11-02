from datetime import datetime
import math
import sys
import logging
import curses


class Plane:
    """A simple SBC Plane class"""
    columns = {0:('ICAO', 7), 1:('Callsign', 11), 2:('Squawk', 7), 3:('Alt', 7), 
        4:('VSpeed', 9), 5:('Track', 7), 6:('Speed(kts)', 12), 7:('Lat', 10), 
        8:('Long', 10), 9:('Nearest Location', 25), 10:('Dist from ant',14), 11:('Evtdt', 12), 12:('>15s', 6), 
        13:('Reg', 9), 14:('Type', 5)}
    # these locations are of interest to me - insert your own - simple 'Name':(digital_lat, digital_long)
    antenna_location = (53.9714887,-1.5415742)
    locations = {'LBA':(53.8736961, -1.6732249), 'Leeds':(53.797365, -1.5580089), 
        'Harrogate':(53.9771475, -1.5430934), 'Skipton':(53.9552364, -2.0219937), 
        'Bradford':(53.7470237, -1.728551), 'Sheffield':(53.3957166, -1.4994562), 
        'Hawes':(54.3040185, -2.198943), 'Doncaster':(53.5188469, -1.1200236), 
        'Wakefield':(53.6782581, -1.3712726), 'Manc-EGCC':(53.2114, -2.1630)}
    planes_of_interest = ['G-OBMS','G-BODE','G-BODB','G-BNOH','G-SACS','G-SACT','G-SACY','G-SACX', 'G-SACP','G-SACW']
    
    callsigns = {}
    conn = None
    dbname = None
       
    def __init__(self, id, now):
        self.id = id
        self.registration = str(id)     #self.get_registration(id)
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
        self.from_antenna = -0.0
        self.eventdate = now	
        self.appeardate = now
        self.active = True
        self.equip = '?'
	     
    
    @classmethod
    def log_observation_end(cls, id, instance):
        sql = 'update observation set endtime = "'+str(datetime.now())+'" where icao_code = "'+id+'" and endtime is null and instance ='+str(instance)
        logging.debug('ending observation with SQL:'+sql)
        cls.conn.execute(sql)
        cls.conn.commit()
    
    def __lt__(self, other):
        return self.appeardate < other.appeardate

    def show(self):
        print "Id=%s callsign=%s squawk=%04d alt=%s track=%s gs=%s lat=%s long=%s" % (self.id, self.callsign, int(self.squawk), self.altitude, self.track, self.gs, self.lat, self.long)
        

        
    @classmethod
    def showheader(cls,win):
        col = 0
        for id in Plane.columns:
            win.addstr(0, col, Plane.columns[id][0])
            col += Plane.columns[id][1]
	

    def showincurses(self, win, row):
        col = 0
        if (datetime.now()-self.eventdate).total_seconds() > 15:
            colour = curses.color_pair(2)
        else:
            colour = curses.color_pair(1)
        for idx in Plane.columns:
            if idx == 0:
                win.addstr(row, col, self.id, colour)
            elif idx == 1:
                win.addstr(row, col, self.callsign, colour)
            elif idx == 2:
                win.addstr(row, col, '{0:04d}'.format(int(self.squawk)), colour)
            elif idx == 3:
                win.addstr(row, col, str(self.altitude), colour)
            elif idx == 4:
                win.addstr(row, col, str(self.vspeed), colour)
            elif idx == 5:
                win.addstr(row, col, '{0:03d}'.format(int(self.track)), colour)
            elif idx == 6:
                win.addstr(row, col, '{0:03d}'.format(int(self.gs)), colour)
            elif idx == 7:
                try:
                    win.addstr(row, col, '{0:2.2f}'.format(float(self.lat)), colour)
                except ValueError:
                    pass
            elif idx == 8:
                try:
                    win.addstr(row, col, '{0:2.2f}'.format(float(self.long)), colour)
                except ValueError:
                    pass
            elif idx == 9:
                if self.nearest != '?':
                    win.addstr(row, col, self.nearest, colour)
            elif idx == 10:
                if self.from_antenna > -0.0:
                    win.addstr(row, col, '{0:3.1f}nm'.format(self.from_antenna), colour)                
            elif idx == 11:
                win.addstr(row, col, str(self.eventdate)[11:19], colour)
            elif idx == 12:
                if (datetime.now()-self.eventdate).total_seconds() > 15:
                    win.addstr(row, col, ' *', colour)
            elif idx == 13:
                if self.registration[:6] in Plane.planes_of_interest:
                    win.addstr(row, col, self.registration, curses.A_REVERSE)
                else:
                    win.addstr(row, col, self.registration, colour)
            elif idx == 14:
                win.addstr(row, col, self.equip, colour)

            col += Plane.columns[idx][1]


    def update(self, parts):
        """
        Update internal representation of each plane based on the contents
        of the update message
        TODO: Would be more efficient to use the message type (parts[1]) to 
        work out which elements are relevant
        """
        if len(parts) >= 16:
            self.active = True      # reactivate if necessary
            can_update_nearest = False
            if len(parts[6]) > 0 and len(parts[7]) > 0:
		try:
                    self.eventdate = datetime.strptime(parts[6] + " " + parts[7], "%Y/%m/%d %H:%M:%S.%f")
                except:
                    logging.debug('Unable to parse 6:{} and 7:{} for datetime'.format(parts[6],parts[7]))
                    pass
            if len(parts[10]) > 0:
                self.callsign = parts[10]
                Plane.callsigns[self.id] = (self.callsign, datetime.now())
            if len(parts[11]) > 0:
                self.altitude = int(float(parts[11]))
            if len(parts[12]) > 0:
                self.gs = int(float(parts[12]))
            if len(parts[13]) > 0:
                self.track = int(float(parts[13]))
            if len(parts[14]) > 0:
                self.lat = parts[14]
                can_update_nearest = True
            if len(parts[15]) > 0:
                self.long = parts[15]
                can_update_nearest = True
            if len(parts[16]) > 0:
                self.vspeed = int(float(parts[16]))
            if len(parts[17]) > 0:
                self.squawk = int(float(parts[17]))

        if can_update_nearest:
            self.update_nearest()

    def update_nearest(self):
        nearest = 400
        
        self.from_antenna=distance_on_sphere(float(self.lat), float(self.long), Plane.antenna_location[0], Plane.antenna_location[1])
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

