import csv
from raptor import Stop, Route, Trip
from pathlib import Path


class GTFSReader:
    def __init__(self):
        self.stops = {}
        self.routes = {}
        self.trips = {}
        self.stop_times = {}


# Folder paths
gtfs_folder = str(Path(__file__).parent.parent) + "/data/gtfs/"
stops_file = gtfs_folder + "stops.txt"
routes_file = gtfs_folder + "routes.txt"
trips_file = gtfs_folder + "trips.txt"
stop_times_file = gtfs_folder + "stop_times.txt"

# 1: Read Stops

# 2: Read Routes

# 3: Read Trips and Stop Times

# 4 Build Route and Trip objects
