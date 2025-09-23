from typing import Dict, Set, List
import csv
from algorithm_prototype.raptor import Stop, Route, Trip
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
        self._read_routes_trips_stoptimes()
        # ...

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

    def _read_routes_trips_stoptimes(self):
        # Step 1: Read routes
        route_data = {}
        with open(self.routes_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: route_id,agency_id,route_stops,route_start,route_end
                route_id = row["route_id"]
                route_name = row["route_start"] + " to " + row["route_end"]
                mode = int(row["agency_id"])  # Use agency_id as mode
                route_data[route_id] = {
                    "name": route_name,
                    "mode": mode,
                    "trips": [],
                    "stops_ids": set(),
                }

        # Step 2: Read stop_times and group by trip_id
        trip_stop_times = {}
        with open(self.stop_times_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: trip_id,arrival_time,departure_time,stop_id,stop_sequence
                trip_id = row["trip_id"]
                stop_id = row["stop_id"]
                arrival_time = row["arrival_time"]
                departure_time = row["departure_time"]
                stop_sequence = int(row["stop_sequence"])
                if trip_id not in trip_stop_times:
                    trip_stop_times[trip_id] = []
                trip_stop_times[trip_id].append(
                    {
                        "stop_id": stop_id,
                        "arrival_time": arrival_time,
                        "departure_time": departure_time,
                        "stop_sequence": stop_sequence,
                    }
                )

        # Step 3: Read trips and build Trip objects, collect stop_ids per route
        with open(self.trips_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: route_id,service_id,trip_id,trip_headsign,direction_id,block_id,shape_id
                trip_id = row["trip_id"]
                route_id = row["route_id"]
                if trip_id not in trip_stop_times:
                    continue  # Skip trips without stop times

                # Sort stops by stop_sequence
                stop_times = sorted(
                    trip_stop_times[trip_id], key=lambda x: x["stop_sequence"]
                )
                stop_ids = [st["stop_id"] for st in stop_times]
                departure_times = []
                for st in stop_times:
                    # Convert HH:MM:SS to mins since midnight
                    h, m, s = map(int, st["departure_time"].split(":"))
                    departure_times.append(h * 60 + m)
                trip = Trip(trip_id, departure_times)
                self.trips[trip_id] = trip
                if route_id in route_data:
                    route_data[route_id]["trips"].append(trip)
                    route_data[route_id]["stops_ids"].update(stop_ids)

        # Step 4: Build Route objects with correct stops and trips
        for route_id, data in route_data.items():
            stop_list = []
            for stop_id in data["stops_ids"]:
                if stop_id in self.stops:
                    stop = self.stops[stop_id]
                    stop.mode = data["mode"]  # Set mode for stop
                    stop_list.append(stop)
            route = Route(route_id, stop_list, data["trips"], name=data["name"])
            self.routes[route_id] = route
