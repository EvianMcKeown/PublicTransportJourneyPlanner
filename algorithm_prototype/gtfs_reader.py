from collections import defaultdict
from typing import Dict, Set, List, Tuple
from os import read
from sys import exception
import sys
import csv
from algorithm_prototype.raptor import (
    Stop,
    Route,
    Trip,
    check_duplicate_stops,
    helper_functions,
)
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

    @staticmethod
    def mins_to_day_hour_min(total_mins: int) -> Tuple[int, int, int]:
        """
        Convert absolute minutes since Monday 00:00 into (day, hour, minute).
        day: 0=Monday, 1=Tuesday, ..., 6=Sunday
        Returns (-1, -1, -1) for INF/None.
        """
        if total_mins is None or total_mins == INF:
            return -1, -1, -1

        MIN_PER_DAY = 24 * 60
        WEEK_MINS = 7 * MIN_PER_DAY

        total = total_mins % WEEK_MINS  # wrap around week
        day = (total // MIN_PER_DAY) % 7
        hour = (total % MIN_PER_DAY) // 60
        minute = (total % MIN_PER_DAY) % 60
        return day, hour, minute

    @staticmethod
    def mins_to_str(total_mins: int) -> str:
        """
        Format minutes since Monday 00:00 as 'Mon HH:MM'. INF/None -> 'N/A'.
        """
        if total_mins is None or total_mins == INF:
            return "N/A"
        day, hh, mm = GTFSReader.mins_to_day_hour_min(total_mins)
        day_names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        if 0 <= day <= 6:
            return f"{day_names[day]} {hh:02d}:{mm:02d}"
        return f"{hh:02d}:{mm:02d}"

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

    @staticmethod
    def _align_by_occurrence(
        canon_ids: List[str], trip_ids: List[str], times: List[int]
    ) -> List[int]:
        """Helper: align trip to canonical by nth occurrence

        Args:
            canon_ids (List[str]): _description_
            trip_ids (List[str]): _description_
            times (List[int]): _description_

        Returns:
            List[int]: _description_
        """
        canon_pos: Dict[str, List[int]] = defaultdict(list)
        for i, sid in enumerate(canon_ids):
            canon_pos[sid].append(i)
        trip_pos: Dict[str, List[int]] = defaultdict(list)
        for j, sid in enumerate(trip_ids):
            trip_pos[sid].append(j)

        used: Dict[str, int] = defaultdict(int)
        aligned = [INF] * len(canon_ids)
        for sid in canon_ids:
            k = used[sid]
            if k < len(trip_pos[sid]) and k < len(canon_pos[sid]):
                src_idx = trip_pos[sid][k]
                dst_idx = canon_pos[sid][k]
                aligned[dst_idx] = times[src_idx]
            used[sid] += 1
        return aligned

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
        """Read routes, trips, stop_times -> build Route objects."""
        # Step 1:
        #   Read calendar.txt to get service_id -> active days mapping
        service_days = self._read_calendar()

        # Collect non-monotonic trips for reporting
        non_monotone_trips: List[str] = []

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
                    case "metrorail":
                        mode = 2  # Train
                    case "MyCiti":
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
                if trip_id not in trip_stop_times:
                    trip_stop_times[trip_id] = []
                trip_stop_times[trip_id].append(
                    {
                        "stop_id": row["stop_id"],
                        "arrival_time": row["arrival_time"],
                        "departure_time": row["departure_time"],
                        "stop_sequence": int(row["stop_sequence"]),
                    }
                )

        # Step 4: Read trips and build Trip objects, collect stop_ids per route
        trips_by_route: Dict[str, List[Dict]] = defaultdict(list)
        with open(self.trips_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # csv format: route_id,service_id,trip_id,trip_headsign,direction_id,block_id,shape_id
                trip_id = row["trip_id"]
                route_id = row["route_id"]
                service_id = row["service_id"]
                direction_id = row["direction_id"]

                if trip_id not in trip_stop_times:
                    continue  # Skip trips without stop times

                # for metrorail trips (mr_*), invert the stop order when direction_id == 1
                is_mr = trip_id.startswith("mr_")
                reverse_order = is_mr and direction_id == "1"

                # Sort stops by stop_sequence - reverse for metrorail trips with direction_id == 1
                rows = sorted(
                    trip_stop_times[trip_id],
                    key=lambda x: x["stop_sequence"],
                    reverse=reverse_order,
                )

                # Keep duplicates to preserve true sequence
                stop_ids = [st["stop_id"] for st in rows]
                departure_times: List[int] = []
                via_mask: List[bool] = (
                    []
                )  # True for VIA stops - will be estimated later

                # Parse times and mark missing with INF
                for st in rows:
                    raw = (st["departure_time"] or "").strip()
                    time_upper = raw.upper()

                    # Treat N/A as having INF time (so it won't affect interpolation)
                    if time_upper in ("N/A", "NA"):
                        departure_times.append(INF)
                        via_mask.append(False)
                        continue
                    # VIA = placeholder time also INF -> mask used to interpolate later
                    if time_upper == "VIA":
                        departure_times.append(INF)
                        via_mask.append(True)
                        continue

                    try:
                        h, m, s = map(int, raw.split(":"))
                        t = h * 60 + m  # daily mins
                        # Convert HH:MM:SS to mins since midnight on monday (next day -> + (24*60)mins)
                        departure_times.append(t)
                        via_mask.append(False)
                    except ValueError:
                        departure_times.append(INF)
                        via_mask.append(False)
                        # missing times = None

                # estimate times for 'VIA' placeholders (N/A stays INF)
                departure_times = helper_functions._estimate_via_times(
                    departure_times, via_mask
                )

                # Check monotone increasing times, if not, raise error
                valid, problem_stop = helper_functions._check_trip_times(
                    departure_times
                )
                if not valid:
                    if isinstance(problem_stop, int) and 0 <= problem_stop < len(
                        stop_ids
                    ):
                        bad_stop_id = stop_ids[problem_stop]
                        bad_seq = rows[problem_stop]["stop_sequence"]
                        prev_t = (
                            departure_times[problem_stop - 1]
                            if problem_stop > 0
                            else None
                        )
                        curr_t = departure_times[problem_stop]
                        non_monotone_trips.append(
                            f"{trip_id} (route={route_id}, service={service_id}, "
                            f"stop_id={bad_stop_id}, seq={bad_seq}, idx={problem_stop}, "
                            f"prev={prev_t}, curr={curr_t})"
                        )
                    else:
                        non_monotone_trips.append(
                            f"{trip_id} (route={route_id}, service={service_id})"
                        )

                # Store trip info for later expansion
                # if route_id not in trips_by_route:
                #    trips_by_route[route_id] = []
                trips_by_route[route_id].append(
                    {
                        "trip_id": trip_id,
                        "service_id": service_id,
                        "departure_times": departure_times,
                        "stop_ids": stop_ids,
                        "direction_id": direction_id,
                    }
                )

        # Step 5: build Route objects with correct stops and modes
        self.routes = {}
        for route_id, meta in route_data.items():
            trip_list = trips_by_route.get(route_id, [])
            if not trip_list:
                continue  # Skip routes without trips

            # choose canonical trip: longest, then most finite times
            canonical = max(
                trip_list,
                key=lambda t: (
                    len(t["stop_ids"]),
                    sum(1 for x in t["departure_times"] if x != INF),
                    t["trip_id"],
                ),
            )
            canonical_stop_ids = canonical["stop_ids"]

            stop_list: List[Stop] = []
            for stop_id in canonical_stop_ids:
                st = self.stops.get(stop_id)
                if st is None:
                    continue
                st.mode = meta["mode"]
                stop_list.append(st)

            route = Route(route_id, stop_list, [], name=meta["name"])
            self.routes[route_id] = route

        # Step 6: Attach Trip objects for each active day in schedule
        for route_id, trip_list in trips_by_route.items():
            route = self.routes.get(route_id)
            if not route:
                continue  # Skip routes without trips
            canonical_ids = [s.id for s in route.stops]

            for trip in trip_list:
                aligned_times = GTFSReader._align_by_occurrence(
                    canonical_ids, trip["stop_ids"], trip["departure_times"]
                )
                active_days = service_days.get(trip["service_id"], [])
                for day_id in active_days:
                    day_offset = day_id * 24 * 60
                    dep_times_for_day = [
                        t + day_offset if t != INF else INF for t in aligned_times
                    ]
                    trip_day_id = f"{trip['trip_id']}_day{day_id}"
                    trip_obj = Trip(trip_day_id, dep_times_for_day)
                    route.add_trip(trip_obj)

        try:
            out_path = Path(self.gtfs_folder + "non_monotone_trips.txt")
            if non_monotone_trips:
                with open(out_path, "w") as f:
                    f.write(
                        "# Trips with non-monotonic departure_times (fix in stop_times/trips)\n"
                    )
                    for trip in non_monotone_trips:
                        f.write(trip + "\n")
        except Exception as e:
            pass
