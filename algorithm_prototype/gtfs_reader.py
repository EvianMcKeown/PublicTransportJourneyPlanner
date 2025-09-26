from os import read
from sys import exception
import sys
from typing import Dict, Set, List
import csv
from algorithm_prototype.raptor import Stop, Route, Trip, helper_functions
from pathlib import Path

INF: int = sys.maxsize
WEEK_MINS = 7 * 24 * 60
WEEKDAY_MULT = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


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
        self.calendar_file = gtfs_folder + "calendar.txt"

        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.trips: Dict[str, Trip] = {}
        self.stop_times: Dict[str, List[Dict]] = {}

        # call methods to read GTFS data - method names start with _ to indicate that they are private
        self._read_stops()
        self._read_routes_trips_stoptimes()
        # ...

    def _read_calendar(self) -> Dict[str, List[int]]:
        """Reads the calendar.txt file and returns a dictionary mapping service_id to list of active days (as offsets).

        Returns:
            Dict[str, List[int]]: service_id -> list of active weekdays (ints 0..6)
        """

        service_days: Dict[str, List[int]] = {}
        with open(self.calendar_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                days = []
                for day, offset in WEEKDAY_MULT.items():
                    if row[day] == "1":
                        days.append(offset)
                service_days[row["service_id"]] = days
        return service_days

    def _expand_trip_days(
        self, cur_route: Route, departure_times: List[int], active_days: List[int]
    ):
        """Expands a list of trip departure times to cover multiple days based on active_days.

        Args:
            departure_times (List[int]): List of departure times in minutes since midnight.
            active_days (List[int]): List of active days as offsets (0=Monday, ..., 6=Sunday).
        """
        for trip_id, trip_info in self.trips.items():
            stop_times: List[int] = self.trips[trip_id].departure_times
            # List of times for this trip

            for day_id in active_days:
                day_offset = day_id * 24 * 60
                departure_times = [t + day_offset for t in departure_times]
                trip_day_id = f"{trip_id}_day{day_id}"
                trip = Trip(trip_day_id, departure_times)
                cur_route.add_trip(trip)

    def _read_stops(self):
        """TODO: _summary_"""
        with open(self.stops_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # OLD (not used) csv format: stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,location_type,parent_station
                # new csv: stop_id,stop_name,stop_lat,stop_lon
                stop_id = row["stop_id"]
                stop_name = row["stop_name"]
                lat = float(row["stop_lat"])
                lon = float(row["stop_lon"])
                # Mode will be set later based on routes
                self.stops[stop_id] = Stop(
                    stop_id, -1, lat, lon, name=stop_name
                )  # mode=-1 -> placeholder

    def _read_routes_trips_stoptimes(self):
        """TODO: _summary_"""
        # Step 1:
        # -> Read calendar.txt to get service_id -> active days mapping
        service_days = self._read_calendar()

        # Step 2: Read routes
        route_data = {}
        with open(self.routes_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: route_id,agency_id,route_short_name
                route_id = row["route_id"]
                route_name = row["route_short_name"]
                agency_id = row["agency_id"]
                match agency_id:
                    case "MetrorailWC":
                        mode = 2  # Train
                    case "MYCITI":
                        mode = 0  # MyCiti Bus
                    case "GABS":
                        mode = 1  # Golden Arrow Bus
                    case _:
                        mode = -1  # Unknown
                        raise ValueError(
                            f"Unknown agency_id '{agency_id}' in routes.txt"
                        )
                route_data[route_id] = {
                    "name": route_name,
                    "mode": mode,
                    "stops_ids": [],
                }

        # Step 3: Read stop_times and group by trip_id
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

        # Step 4: Read trips and build Trip objects, collect stop_ids per route
        trips_by_route = {}
        with open(self.trips_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: route_id,service_id,trip_id,trip_headsign,direction_id,block_id,shape_id
                trip_id = row["trip_id"]
                route_id = row["route_id"]
                service_id = row["service_id"]

                if trip_id not in trip_stop_times:
                    continue  # Skip trips without stop times

                # Sort stops by stop_sequence
                stop_times = sorted(
                    trip_stop_times[trip_id], key=lambda x: x["stop_sequence"]
                )

                # Remove duplicate stops on a trip - use only last occurrence.
                stops_cleaned = {}
                for st in stop_times:
                    stops_cleaned[st["stop_id"]] = st  # overwrites earlier occurrence
                stop_times = list(stops_cleaned.values())
                # rebuild ordered list
                stop_times.sort(key=lambda x: x["stop_sequence"])
                stop_ids = [st["stop_id"] for st in stop_times]
                departure_times = []

                # Parse times and mark missing with INF
                for st in stop_times:
                    time_str = st["departure_time"].strip()
                    if time_str == "" or time_str is None:
                        departure_times.append(INF)
                        continue

                    try:
                        h, m, s = map(int, time_str.split(":"))
                        t = h * 60 + m  # daily mins
                        # Convert HH:MM:SS to mins since midnight on monday (next day -> + (24*60)mins)
                        departure_times.append(t)
                    except ValueError:
                        departure_times.append(INF)  # missing times = None

                # Interpolate missing times that are "bounded" by known times
                i = 0
                while i < len(departure_times):
                    if departure_times[i] == INF:
                        # Find start and end of missing segment
                        start = i - 1
                        j = i
                        while j < len(departure_times) and departure_times[j] == INF:
                            j += 1
                        end = j

                        if start >= 0 and end < len(departure_times):
                            t_start = departure_times[start]
                            t_end = departure_times[end]
                            num_missing = end - start - 1
                            for cur_stop in range(1, num_missing + 1):
                                # Linear interpolation — TODO: could be improved with haversine distance
                                # TODO: handle wrap-around at midnight (e.g., 23:50 to 00:10)
                                interpolated = t_start + (
                                    t_end - t_start
                                ) * cur_stop / (num_missing + 1)
                                departure_times[start + cur_stop] = int(interpolated)
                        # leave missing stops as INF if not bounded on both sides (as if the stop is
                        # not served on this trip)
                        i = end
                    else:
                        i += 1
                    if i >= len(departure_times):
                        break

                # Collect stop_ids for this route
                if route_id in route_data:
                    if route_id == "mc_101":
                        print()
                    for sid in stop_ids:
                        if sid not in route_data[route_id]["stops_ids"]:
                            route_data[route_id]["stops_ids"].append(sid)
                else:
                    raise ValueError(
                        f"route_id '{route_id}' for trip_id '{trip_id}' not found in routes.txt"
                    )

                # Store trip info for later expansion
                if route_id not in trips_by_route:
                    trips_by_route[route_id] = []
                trips_by_route[route_id].append(
                    {
                        "trip_id": trip_id,
                        "departure_times": departure_times,
                        "service_id": service_id,
                    }
                )

        # Step 5: build Route objects with correct stops and modes
        for route_id, data in route_data.items():
            if route_id == "mc_101":
                print()
            stop_list = []
            for stop_id in data["stops_ids"]:
                if stop_id in self.stops:
                    stop = self.stops[stop_id]
                    stop.mode = data["mode"]
                    stop_list.append(stop)
            route = Route(route_id, stop_list, [], name=data["name"])
            self.routes[route_id] = route

        # Step 6: Attach Trip objects for each active day in schedule
        for route_id, trips in trips_by_route.items():
            route = self.routes[route_id]
            for trip_info in trips:
                trip_id = trip_info["trip_id"]
                departure_times = trip_info["departure_times"]
                service_id = trip_info["service_id"]
                active_days = self._read_calendar().get(service_id, [])
                for day_id in active_days:
                    day_offset = day_id * 24 * 60
                    dep_times_for_day = [
                        t + day_offset if t != INF else INF for t in departure_times
                    ]
                    trip_day_id = f"{trip_id}_day{day_id}"
                    trip = Trip(trip_day_id, dep_times_for_day)
                    if route.id == "mc_101":
                        print()
                    route.add_trip(trip)
