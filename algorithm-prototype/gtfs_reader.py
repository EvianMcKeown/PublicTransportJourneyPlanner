from typing import Dict, Set, List
import csv
from raptor import Stop, Route, Trip
from pathlib import Path


class GTFSReader:
    def __init__(self, gtfs_folder=None):
        if gtfs_folder is None:
            gtfs_folder = str(Path(__file__).parent.parent) + "/data/gtfs/"
        self.gtfs_folder = gtfs_folder
        # Folder paths
        self.stops_file = gtfs_folder + "stops.txt"
        self.routes_file = gtfs_folder + "routes.txt"
        self.trips_file = gtfs_folder + "trips.txt"
        self.stop_times_file = gtfs_folder + "stop_times.txt"

        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.trips: Dict[str, Trip] = {}
        self.stop_times: Dict[str, List[Dict]] = {}

        # call methods to read GTFS data - method names start with _ to indicate that they are private
        self._read_stops()
        self._read_routes()
        self._read_trips_and_stoptimes()
        self._build_routes_with_trips()

    def _read_stops(self):
        with open(self.stops_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,location_type,parent_station
                stop_id = row["stop_id"]
                stop_name = row["stop_name"]
                lat = float(row["stop_lat"])
                lon = float(row["stop_lon"])
                # Mode will be set later based on routes
                self.stops[stop_id] = Stop(
                    stop_id, -1, lat, lon, name=stop_name
                )  # mode=-1 -> placeholder

    def _read_routes(self):
        self.route_modes = {}
        with open(self.routes_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: route_id,agency_id,route_stops,route_start,route_end
                route_id = row["route_id"]
                route_name = row["route_start"] + " to " + row["route_end"]
                route_stops
                mode = int(row["agency_id"])  # Use agency_id as mode
                self.route_modes[route_id] = mode
                self.routes[route_id] = Route(route_id, route_name, mode)

    # 1: Read Stops
    stops = {}
    with open(stops_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row["stop_id"]
            stop_name = row["stop_name"]
            mode = 2  # Set mode based on your mapping
            lat = float(row["stop_lat"])
            lon = float(row["stop_lon"])
            stops[stop_id] = Stop(stop_id, mode, lat, lon)
            # TODO: Add name to Stop class

    # 2: Read Routes
    routes = {}
    with open(routes_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # route_id,agency_id,route_stops,route_start,route_end
            route_id = row["route_id"]
            route_name = row["route_long_name"]
            mode = int(row["agency_id"])  # TODO: change mode of stops
            routes[route_id] = Route(route_id, route_name, mode)

    # 3: Read Trips and Stop Times

    # 4 Build Route and Trip objects
