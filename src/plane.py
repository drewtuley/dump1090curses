import curses
import logging
import math
import sys
import time
from datetime import datetime
from functools import total_ordering

STALE_DATA_SECONDS = 15

FARTHER_THAN_THE_NEAREST_LOCATION = 400

MAX_POSSIBLE_RANGE = 1000

CACHE_EXPIRY = 30 * 60


@total_ordering
class Plane:
    """A simple SBC Plane class"""

    columns = {
        0: ("ICAO", 7),
        1: ("Callsign", 11),
        2: ("Squawk", 7),
        3: ("Alt", 7),
        4: ("VSpeed", 9),
        5: ("Track", 7),
        6: ("Speed", 7),
        7: ("Lat", 8),
        8: ("Long", 8),
        9: ("Nearest Location", 32),
        10: ("Dist/ant", 15),
        11: ("Evtdt", 12),
        12: (">15s", 5),
        13: ("Reg", 10),
        14: ("Type", 6),
        15: ("#PMs", 5),
    }
    # these locations are of interest to me - insert your own - simple 'Name':(digital_lat, digital_long)
    antenna_location = (53.978614, -1.528686)
    locations = {
        "LBA": (53.8736961, -1.6732249),
        "Leeds": (53.797365, -1.5580089),
        "Harrogate": (53.9771475, -1.5430934),
        "Skipton": (53.9552364, -2.0219937),
        "Bradford": (53.7470237, -1.728551),
        "Sheffield": (53.3957166, -1.4994562),
        "Hawes": (54.3040185, -2.198943),
        "Doncaster": (53.5188469, -1.1200236),
        "Wakefield": (53.6782581, -1.3712726),
        "Manc-EGCC": (53.2114, -2.1630),
    }
    planes_of_interest = [
        "G-OBMS",
        "G-BODE",
        "G-BODB",
        "G-BNOH",
        "G-SACS",
        "G-SACT",
        "G-SACY",
        "G-SACX",
        "G-SACP",
        "G-SACW",
    ]

    callsigns = {}

    def __init__(self, id, now):
        self.id = id
        self.registration = str(id)  # self.get_registration(id)
        if id in Plane.callsigns.keys():
            cachetime = Plane.callsigns[id][1]
            if (datetime.now() - cachetime).total_seconds() > CACHE_EXPIRY:
                del Plane.callsigns[id]
                self.callsign = "?"
            elif not Plane.callsigns[id][0].endswith("*"):
                self.callsign = Plane.callsigns[id][0] + "*"
        else:
            self.callsign = "?"

        self._altitude = 0
        self._altitude_ts = 0
        self._vspeed = 0
        self._vspeed_ts = 0
        self._squawk = "0"
        self._squawk_ts = 0
        self._track = 0
        self._track_ts = 0
        self._gs = 0
        self._gs_ts = 0
        self._lat = ""
        self._lat_ts = 0
        self._long = ""
        self._long_ts = 0

        self._nearest = "?"
        self._nearest_ts = 0
        self._dist_from_antenna = -0.0
        self._dist_from_antenna_ts = 0
        self._dir_from_antenna = "???"
        self._dir_from_antenna_ts = 0
        self.eventdate = now
        self.appeardate = now
        self.active = True
        self.equip = "?"
        self.posmsgs = 0
        self.STALE_DISPLAY = 30

    @property
    def altitude(self):
        if time.time() - self._altitude_ts > self.STALE_DISPLAY:
            self._altitude = 0
        return self._altitude

    @altitude.setter
    def altitude(self, value):
        self._altitude = value
        self._altitude_ts = time.time()

    @property
    def squawk(self):
        if time.time() - self._squawk_ts > self.STALE_DISPLAY:
            self._squawk = "0"
        return self._squawk

    @squawk.setter
    def squawk(self, value):
        self._squawk = value
        self._squawk_ts = time.time()

    @property
    def vspeed(self):
        if time.time() - self._vspeed_ts > self.STALE_DISPLAY:
            self._vspeed = 0
        return self._vspeed

    @vspeed.setter
    def vspeed(self, value):
        self._vspeed = value
        self._vspeed_ts = time.time()

    @property
    def track(self):
        if time.time() - self._track_ts > self.STALE_DISPLAY:
            self._track = 0
        return self._track

    @track.setter
    def track(self, value):
        self._track = value
        self._track_ts = time.time()

    @property
    def gs(self):
        if time.time() - self._gs_ts > self.STALE_DISPLAY:
            self._gs = 0
        return self._gs

    @gs.setter
    def gs(self, value):
        self._gs = value
        self._gs_ts = time.time()

    @property
    def lat(self):
        if time.time() - self._lat_ts > self.STALE_DISPLAY:
            self._lat = ""
        return self._lat

    @lat.setter
    def lat(self, value):
        self._lat = value
        self._lat_ts = time.time()

    @property
    def long(self):
        if time.time() - self._long_ts > self.STALE_DISPLAY:
            self._long = ""
        return self._long

    @long.setter
    def long(self, value):
        self._long = value
        self._long_ts = time.time()

    @property
    def nearest(self):
        if time.time() - self._nearest_ts > self.STALE_DISPLAY:
            self._nearest = "?"
        return self._nearest

    @nearest.setter
    def nearest(self, value):
        self._nearest = value
        self._nearest_ts = time.time()

    @property
    def dist_from_antenna(self):
        if time.time() - self._dist_from_antenna_ts > self.STALE_DISPLAY:
            self._dist_from_antenna = -0.0
        return self._dist_from_antenna

    @dist_from_antenna.setter
    def dist_from_antenna(self, distance):
        self._dist_from_antenna = distance
        self._dist_from_antenna_ts = time.time()

    @property
    def dir_from_antenna(self):
        if time.time() - self._dir_from_antenna_ts > self.STALE_DISPLAY:
            self._dir_from_antenna = ""
        return self._dir_from_antenna

    @dir_from_antenna.setter
    def dir_from_antenna(self, direction):
        self._dir_from_antenna = direction
        self._dir_from_antenna_ts = time.time()

    def __lt__(self, other):
        x = self.dist_from_antenna
        y = other.dist_from_antenna
        if x <= 0:
            x = MAX_POSSIBLE_RANGE
        if y <= 0:
            y = MAX_POSSIBLE_RANGE
        return x < y

    def __eq__(self, other):
        return self.dist_from_antenna == other.dist_from_antenna

    def show(self):
        print(
            "Id=%s callsign=%s squawk=%04d alt=%s track=%s gs=%s lat=%s long=%s"
            % (
                self.id,
                self.callsign,
                int(self.squawk),
                self.altitude,
                self.track,
                self.gs,
                self.lat,
                self.long,
            )
        )

    def __repr__(self):
        return "id: {id} c/s: {cs} reg: {reg} alt:{alt} track:{track} gs:{gs} lat:{lat} long:{long}".format(
            id=self.id,
            cs=self.callsign,
            reg=self.registration,
            alt=self.altitude,
            track=self.track,
            gs=self.gs,
            lat=self.lat,
            long=self.long,
        )

    @classmethod
    def showheader(cls, win):
        col = 0
        for id in Plane.columns:
            win.addstr(0, col, Plane.columns[id][0])
            col += Plane.columns[id][1]

    def _get_display_data(self):
        """Extract display data from plane attributes"""
        is_stale = (
            datetime.now() - self.eventdate
        ).total_seconds() > STALE_DATA_SECONDS
        is_interesting = self.registration[:6] in Plane.planes_of_interest

        data = {
            0: self.id,
            1: self.callsign,
            2: "{0:04d}".format(int(self.squawk)),
            3: str(self.altitude),
            4: str(self.vspeed),
            5: "{0:03d}".format(int(self.track)),
            6: "{0:03d}".format(int(self.gs)),
            7: "{0:2.2f}".format(float(self.lat)) if self.lat else "",
            8: "{0:2.2f}".format(float(self.long)) if self.long else "",
            9: self.nearest if self.nearest != "?" else "",
            10: (
                "{0:5.1f}nm {1:>4s}".format(
                    self.dist_from_antenna, self.dir_from_antenna
                )
                if self.dist_from_antenna > -0.0
                else ""
            ),
            11: str(self.eventdate)[11:19],
            12: " *" if is_stale else "",
            13: self.registration,
            14: str(self.equip),
            15: str(self.posmsgs),
        }

        return data, is_stale, is_interesting

    def showincurses(self, win, row):
        """Display plane data in curses window"""
        data, is_stale, is_interesting = self._get_display_data()
        colour = curses.color_pair(2) if is_stale else curses.color_pair(1)

        col = 0
        for idx in Plane.columns:
            if data[idx]:
                attr = curses.A_REVERSE if idx == 13 and is_interesting else colour
                try:
                    win.addstr(row, col, data[idx], attr)
                except ValueError:
                    pass
            col += Plane.columns[idx][1]

    def update(self, parts):
        """
        Update internal representation of each plane based on the contents
        of the update message
        TODO: Would be more efficient to use the message type (parts[1]) to
        work out which elements are relevant
        """
        can_update_nearest = False
        if len(parts) >= 16:
            self.active = True  # reactivate if necessary
            if len(parts[6]) > 0 and len(parts[7]) > 0 and len(parts[0]) > 0:
                try:
                    self.eventdate = datetime.strptime(
                        parts[6] + " " + parts[7], "%Y/%m/%d %H:%M:%S.%f"
                    )
                except:
                    logging.debug(
                        "Unable to parse 6:{} and 7:{} for datetime".format(
                            parts[6], parts[7]
                        )
                    )
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
            self.posmsgs += 1

    def update_nearest(self):
        """
        Update this Plane with its nearest location from the predefined list
        and also its distance from the antenna location
        """
        nearest: float = FARTHER_THAN_THE_NEAREST_LOCATION

        self.dist_from_antenna = distance_on_sphere(
            float(self.lat),
            float(self.long),
            Plane.antenna_location[0],
            Plane.antenna_location[1],
        )
        br1 = bearing(
            Plane.antenna_location[0],
            Plane.antenna_location[1],
            float(self.lat),
            float(self.long),
        )
        self.dir_from_antenna = cardinal(br1)
        for location in Plane.locations:
            data = Plane.locations[location]
            distance = distance_on_sphere(
                float(self.lat), float(self.long), (data[0]), (data[1])
            )
            if distance < nearest:
                nearest = distance
                br = bearing(data[0], data[1], float(self.lat), float(self.long))
                self.nearest = "{0:-5.1f}nm {1:3} {2}".format(
                    distance, cardinal(br), location
                )


def distance_on_sphere(lat1, long1, lat2, long2) -> float:
    """
    Courtesy of http://www.johndcook.com/blog/python_longitude_latitude/
    """
    deg_to_rad = math.pi / 180.0

    phi1 = (90.0 - lat1) * deg_to_rad
    phi2 = (90.0 - lat2) * deg_to_rad

    theta1 = long1 * deg_to_rad
    theta2 = long2 * deg_to_rad

    cos = math.sin(phi1) * math.sin(phi2) * math.cos(theta1 - theta2) + math.cos(
        phi1
    ) * math.cos(phi2)
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

    y = math.sin(rlong2 - rlong1) * math.cos(rlat2)
    x = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(
        rlat2
    ) * math.cos(rlong2 - rlong1)
    b = math.atan2(y, x) / (math.pi / 180.0)
    b = (b + 360.0) % 360.0
    return b


def cardinal(bearing):
    compass = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
        "N",
    ]
    return compass[int((bearing + 11) / 22)]


if len(sys.argv) > 1 and sys.argv[1] == "test":
    testplane = Plane("AABBCC", datetime.now())

    # test distance_on_sphere
    leeds = Plane.locations["Leeds"]
    plane = (54.82433, -2.12970)

    print("{0:3.2f}".format(distance_on_sphere(leeds[0], leeds[1], plane[0], plane[1])))
    print(bearing(leeds[0], leeds[1], plane[0], plane[1]))

    harrogate = Plane.locations["Harrogate"]
    print(
        "{0:3.2f}".format(
            distance_on_sphere(leeds[0], leeds[1], harrogate[0], harrogate[1])
        )
    )
    print(bearing(leeds[0], leeds[1], harrogate[0], harrogate[1]))

    for b in range(0, 360, 5):
        print(str(b) + " " + cardinal(b))

    for loc in Plane.locations:
        print(loc)

    update = [
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "53.123456",
        "-1.5223123",
        "",
        "",
        "",
        "",
    ]
    testplane.update(update)
    print(testplane.nearest)

    Plane.callsigns["AABBCCDD"] = ("Hellcat", datetime.now())
    update = [
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "Pussy",
        "",
        "",
        "",
        "53.123456",
        "-1.5223123",
        "",
        "",
        "",
        "",
    ]
    testplane2 = Plane("AABBCCDD", datetime.now())
    print(testplane2.callsign)
    testplane2.update(update)
    print(testplane2.callsign)
