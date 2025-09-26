### version 1
# import multiprocessing as mp
from dataclasses import dataclass, field
from email.policy import default
from os import name
import queue
from re import I
import sys
from tracemalloc import stop
from typing import Any, List, Dict, Optional, Tuple
from math import ceil, radians, cos, sin, asin, sqrt  # Haversine formula

# Value used as INFINITY
INF: int = sys.maxsize
MAX_WALK_DIST = 3000  # maximum walkable distance in meters
WALKING_SPEED = 5 * 1000 / 60
MIN_TRANSFER_TIME = 2


@dataclass
class Stop:
    """each stop corresponds to a (distinct) location,
    where a commuter can board or get off a vehicle (train, bus, etc.)"""

    id: str
    mode: int  # 0=GoldenArrow, 1=MyCiti, 2=Train
    lat: float
    lon: float
    name: str = ""

    earliest_arrival: Dict[int, int] = field(default_factory=dict)  # round -> time
    # earliest arrival time per round, updated in algo
    # can alternatively store earliest arrival time as a two dimensional array


@dataclass
class Trip:
    """a time dependant sequence of stops a specific vehicle (train, bus, etc.)
    makes on a line (route) - at each stop it may pick up or drop-off passengers
    """

    id: str
    # stops: List[Stop]
    # route: "Route"
    departure_times: List[
        int
    ]  # departure times at corresponding stops (from associated route)


@dataclass
class Route:
    """ordered list of stops and the trips coinciding with them. No time info here.
    TODO maybe make a single list contain all this for a DOD approach?"""

    id: str
    stops: List[Stop]  # can remove duplication of stops between routes and trips later
    trips: List[Trip] = field(default_factory=list)
    name: str = ""

    @property
    def mode(self) -> int:
        return self.stops[0].mode if self.stops else -1

    def add_trip(self, trip: Trip):
        # Ensure trip matches stop count
        # TODO check that no duplicate trips
        if len(self.stops) != len(trip.departure_times):
            trip_dep_list = trip.departure_times
            route_stops = self.stops
            raise ValueError(
                f"Error: Trip {trip.id} has {len(trip.departure_times)} departure times ({trip_dep_list}), but route {self.id} has {len(self.stops)} stops ({route_stops})."
            )
        # assert len(trip.departure_times) == len(self.stops)
        self.trips.append(trip)


@dataclass
class Transfer:
    """TODO"""

    from_stop: Stop
    to_stop: Stop
    walking_time: int  # time in minutes


class helper_functions:
    @staticmethod
    def check_mode(transport_mode: str) -> int:
        match transport_mode:
            case "train":
                return 1
            case "myciti":
                return 2
            case "goldenarrow":
                return 3
            case "taxi":
                return 4
        # if invalid string, return -1
        return -1

    @staticmethod
    def stops_same_mode(stops: Dict[str, Stop]) -> bool:
        s0 = next(iter(stops.values()))
        for s in stops.values():
            if s0.mode != s.mode:
                return False
        return True

    @staticmethod
    def haversine(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
        """Return distance in meters between two coordinates using Haversine
            formula with mean earth radius.
            Haversine formula - https://en.wikipedia.org/wiki/Haversine_formula

        Args:
            lat_a (float): latitude of coordinate a lon_a (float): longitude of
            coordinate a lat_b (float): latitude of coordinate b lon_b (float):
            longitude of coordinate b

        Returns:
            float: distance in meters
        """

        # degree to radian
        lat_a, lon_a, lat_b, lon_b = map(radians, [lat_a, lon_a, lat_b, lon_b])
        # get deltas
        delta_lat = lat_b - lat_a  # y
        delta_lon = lon_b - lon_a  # x
        a = sin(delta_lat / 2) ** 2 + sin(delta_lon / 2) ** 2 * cos(lat_a) * cos(lat_b)
        b = 2 * 6371 * 1000 * asin(sqrt(a))  # meters

        return b

    @staticmethod
    def walkable(
        lat_a: float, lon_a: float, lat_b: float, lon_b: float, dist=500
    ) -> bool:
        """
        Determines if two positions, a and b, are less than some maximum
        distance from each other. If so, then they can be used to move from one
        route to another.

        Args:
            lat_a (float): latitude of coordinate a lon_a (float): longitude of
            coordinate a lat_b (float): latitude of coordinate b lon_b (float):
            longitude of coordinate b dist (int): maximum walking distance in
            meters

        Returns:
            boolean: walkable
        """

        # Haversine formula - https://en.wikipedia.org/wiki/Haversine_formula

        return helper_functions.haversine(lat_a, lon_a, lat_b, lon_b) <= dist

    @staticmethod
    def create_transfers(
        stops: Dict[str, Stop],
        max_walking_dist: int = MAX_WALK_DIST,
        min_transfer_time: int = MIN_TRANSFER_TIME,
        walking_speed: float = WALKING_SPEED,
    ) -> List[Transfer]:
        """Creates transfers between all stops that are walkable within the specified maximum walking distance.

        Args:
            stops (Dict[str, Stop]): Stops to consider for transfers.
            max_walking_dist (int, optional): Maximum distance to create transfers between. Defaults to MAX_WALK_DIST.
            min_transfer_time (int, optional): Minimum time to complete a transfer. Defaults to MIN_TRANSFER_TIME.
            walking_speed (float, optional): Speed of travel -> Determines time taken. Defaults to WALKING_SPEED.

        Returns:
            List[Transfer]: List of transfers between stops.
        """

        # determine if walkable
        transfers: List[Transfer] = []
        for s1 in stops.values():
            for s2 in stops.values():
                if s1.id != s2.id:
                    distance = helper_functions.haversine(
                        s1.lat, s1.lon, s2.lat, s2.lon
                    )
                    # print(distance)
                    if distance <= max_walking_dist:
                        walk_time_minutes = max(
                            min_transfer_time, ceil(distance / walking_speed)
                        )
                        transfers.append(Transfer(s1, s2, walk_time_minutes))
        return transfers

    @staticmethod
    def create_transfer_map(
        transfers: List[Transfer],
    ) -> Dict[Tuple[str, str], Transfer]:
        """Creates dictionary mapping (from_stop_id, to_stop_id) to the Transfer object.

        Args:
            transfers (List[Transfer]): List of all transfers.

        Returns:
            Dict[Tuple[str, str], Transfer]: Mapping of (from_stop_id, to_stop_id) to Transfer object.
        """
        transfer_map: Dict[Tuple[str, str], Transfer] = {}
        for t in transfers:
            # Use IDs as keys
            transfer_map[(t.from_stop.id, t.to_stop.id)] = t
        return transfer_map


def raptor_algo(
    stops: Dict[str, Stop],
    routes: Dict[str, Route],
    transfers: List[Transfer],
    source_id: str,
    target_id: str,
    departure_time: int,
    max_rounds: int = 10,
) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """RAPTOR - Round bAsed Public Transit Optimised Router.

    v1: unoptimised

    Args:
        TODO

    Returns:
        Tuple[Dict[str, int], List[Optional[Dict]]]:
            - Dict of earliest arrival times at all stops.
            - List of steps (the reconstructed fastest path from source to target).
    """

    # build index mapping for array storage
    stop_ids = list(stops.keys())
    id_to_idx: Dict[str, int] = {sid: i for i, sid in enumerate(stop_ids)}
    idx_to_id: Dict[int, str] = {i: sid for sid, i in id_to_idx.items()}
    n = len(stops.keys())

    # adjacency lists for transfers (indices) - walking time from stop u to v
    # TODO: THIS TAKES STUPIDLY LONG - DO IN PREPROCESSING
    transfer_adj: List[List[Tuple[int, int]]] = [[] for _ in range(n)]
    for t in transfers:
        u = id_to_idx[t.from_stop.id]
        v = id_to_idx[t.to_stop.id]
        transfer_adj[u].append((v, t.walking_time))

    # compute route-stop indices
    routes_stop_indices: Dict[str, List[int]] = {}
    for rid, route in routes.items():
        routes_stop_indices[rid] = [id_to_idx[s.id] for s in route.stops]

    # earliest arrival time for each stop over all rounds
    best = [INF] * n
    prev = [INF] * n
    cur = [INF] * n

    # initialise
    if source_id not in id_to_idx:
        raise ValueError("Origin not a valid Stop.")
    source_idx = id_to_idx[source_id]

    best[source_idx] = departure_time
    prev[source_idx] = departure_time
    cur[source_idx] = departure_time

    # marked stops: those improved in the last round (init to only source)
    marked = [False] * n
    marked[source_idx] = True
    marked_list = [source_idx]

    # store predecessors for path reconstruction
    # each entry is a dict with keys: prev_idx, arrival_time, mode, route_id, trip_id, transfer_time
    # or None if no predecessor (initially)
    predecessor: List[Optional[Dict]] = [None] * n

    # main round
    for k in range(1, max_rounds + 1):
        improved = False

        # 1: Accumulate routes serving marked stops from previous round
        Q: List[Tuple[str, int]] = []  # (route_id, first_marked_stop_index_in_route)
        for rid, route in routes.items():
            stop_indices = routes_stop_indices[rid]
            # find first marked index in the route
            first_marked_pos = None
            for pos, stop_idx in enumerate(stop_indices):
                if marked[stop_idx]:
                    first_marked_pos = pos
                    break
            if first_marked_pos is not None:
                Q.append((rid, first_marked_pos))

        # reset marked for this round — will mark as we improve earliest times
        marked = [False] * n
        marked_list = []

        # 2: Traverse each route
        for rid, start_pos in Q:
            cur_route = routes[rid]
            stop_indices = routes_stop_indices[rid]
            num_stops_in_route = len(stop_indices)

            for trip in cur_route.trips:
                # check whether we can board the trip (on this route) at any stop
                # Try to board at earliest possible stop
                boarded_at = None
                for pos in range(start_pos, num_stops_in_route):
                    stop_idx = stop_indices[pos]
                    arr_prev = prev[stop_idx]
                    if arr_prev == INF:
                        continue  # if we cannot reach stop, then ignore
                    trip_departure = trip.departure_times[pos]

                    if trip_departure >= arr_prev:
                        boarded_at = pos
                        break  # board at first possible stop, and stop checking

                if boarded_at is None:
                    # can't use this trip from any marked stop
                    continue

                # move along trip from boarded_at stop
                # -> start look form stop after the boarding_at stop
                for pos2 in range(boarded_at + 1, num_stops_in_route):
                    stop_idx2 = stop_indices[pos2]
                    # arrival time at stop_idx2
                    trip_time = trip.departure_times[pos2]
                    prev_stop_idx = stop_indices[pos2 - 1]

                    if trip_time < cur[stop_idx2]:
                        if stop_idx2 == source_idx and trip_time > departure_time:
                            # Don't overwrite source with later time
                            continue

                        cur[stop_idx2] = trip_time
                        best[stop_idx2] = min(best[stop_idx2], trip_time)

                        if not marked[stop_idx2]:
                            marked[stop_idx2] = True
                            marked_list.append(stop_idx2)
                            improved = True

                        # update predecessor
                        predecessor[stop_idx2] = {
                            "prev_idx": prev_stop_idx,
                            "arrival_time": trip_time,
                            "mode": "trip",
                            "route_id": rid,
                            "trip_id": trip.id,
                            "transfer_time": None,
                        }

        # 3: Look at foot-paths (transfers) — since we have no chained walks and
        # we are using a fixed distance based formula for walking time, all we
        # have to do is 'walk' through (pardon the pun) each transfer.
        for p in marked_list:
            arr_p = cur[p]
            if arr_p == INF:
                continue

            for v, walk_time in transfer_adj[p]:
                new_arrival = arr_p + walk_time
                if new_arrival < cur[v]:
                    cur[v] = new_arrival
                    best[v] = min(best[v], new_arrival)

                    # transfers can mark a stop not reached by a trip
                    if not marked[v]:
                        marked[v] = True
                        marked_list.append(v)
                        improved = True
                    # update predecessor
                    predecessor[v] = {
                        "prev_idx": p,
                        "arrival_time": new_arrival,
                        "mode": "transfer",
                        "route_id": None,
                        "trip_id": None,
                        "transfer_time": walk_time,
                    }

        if not improved:
            break

        prev = cur[:]  # shallow copy list (values, not references)
        cur = [INF] * n

    # finalize earliest arrival times dict
    best[source_idx] = departure_time  # reset source to departure time
    result: Dict[str, int] = {}
    for i, sid in idx_to_id.items():
        result[sid] = best[i]

    # reconstruct path
    if target_id not in id_to_idx or result[target_id] == INF:
        # no path to target
        return result, []
    target_idx = id_to_idx[target_id]
    journey = reconstruct_path(predecessor, idx_to_id, target_idx, source_idx, result)

    return result, journey


def reconstruct_path(
    predecessor, idx_to_id, target_idx, source_idx, result: Dict[str, int]
):
    """TODO: _summary_

    Args:
        predecessor (_type_): _description_
        idx_to_id (_type_): _description_
        target_idx (_type_): _description_
        source_idx (_type_): _description_
        result (Dict[str, int]): _description_

    Returns:
        _type_: _description_
    """
    path: List[Dict] = []
    current = target_idx

    # trace from target back to source
    while current != source_idx and predecessor[current] is not None:
        step = predecessor[current].copy()
        step["stop_id"] = idx_to_id[current]
        step["from_stop_id"] = idx_to_id[step["prev_idx"]]
        path.append(step)
        current = step["prev_idx"]

    # If the trace stops before the source, something went wrong, or the source
    # was reached via a transfer that wasn't recorded properly (which is unlikely
    # for the initial source stop). We rely on the initial check for path existence.
    if current != source_idx:
        # Path trace failed to reach the source, return empty
        empty_path: List[Dict] = []
        return empty_path

    # add source stop as starting point
    path.append(
        {
            "stop_id": idx_to_id[source_idx],
            "arrival_time": result[idx_to_id[source_idx]],
            "mode": "start",
            "route_id": None,
            "trip_id": None,
            "transfer_time": None,
            "from_stop_id": None,
        }
    )
    path.reverse()
    return path


def reconstruct_path_objs(
    path: List[Dict[str, Any]],
    stops_dict: Dict[str, "Stop"],
    routes_dict: Dict[str, "Route"],
    transfers_dict: Dict[Tuple[str, str], Transfer],
) -> List[Dict[str, Any]]:
    """Convert path with IDs to path with Stop, Route, and Trip objects.

    Args:
        path (List[Dict[str, Any]]): Path returned by RAPTOR with stop and route IDs.
        stops_dict (Dict[str, Stop]): Dictionary of all Stop objects by ID.
        routes_dict (Dict[str, Route]): Dictionary of all Route objects by ID.

    Returns:
        List[Dict[str, Any]]: Path with Stop and Route object references.
    """
    path_objs: List[Dict[str, Any]] = []
    for step in path:
        new_step = step.copy()

        # Find Stop objects
        # stop_id is the arrival stop for this step
        if new_step.get("stop_id") in stops_dict:
            new_step["stop_object"] = stops_dict[new_step["stop_id"]]

        # from_stop_id is the departure stop for this step
        if new_step.get("from_stop_id") in stops_dict:
            new_step["from_stop_object"] = stops_dict[new_step["from_stop_id"]]

        # Find Route and Trip objects (only for trip steps)
        if new_step["mode"] == "trip":
            route_id = new_step.get("route_id")
            trip_id = new_step.get("trip_id")

            if route_id in routes_dict:
                route = routes_dict[route_id]
                new_step["route_object"] = route

                # Find specific Trip object within route
                if trip_id:
                    trip = next((t for t in route.trips if t.id == trip_id), None)
                    new_step["trip_object"] = trip

        # Find Transfer object (only for transfer steps)
        elif new_step["mode"] == "transfer":
            from_id = new_step.get("from_stop_id")
            to_id = new_step.get("stop_id")

            if from_id and to_id:
                transfer_key = (from_id, to_id)
                if transfer_key in transfers_dict:
                    new_step["transfer_object"] = transfers_dict[transfer_key]

        path_objs.append(new_step)
    return path_objs


if __name__ == "__main__":
    from gtfs_reader import GTFSReader

    gtfs = GTFSReader()
    stops = gtfs.stops
    routes = gtfs.routes
    trips = gtfs.trips

    # Example Stops
    a = Stop("Greenpoint", 2, -33.918, 18.423)
    b = Stop("Gardens", 2, -33.935, 18.413)
    c = Stop("Observatory", 2, -34.05, 18.35)

    # stops = {s.id: s for s in [a, b, c]}
    # stops = [a, b, c]

    # Example Routes
    # route_example = Route("A", [a, b, c])
    # route_example.add_trip(Trip("A-1", [7 * 60, 7 * 60 + 10, 7 * 60 + 30]))
    # route_example.add_trip(Trip("A-2", [7 * 60 + 20, 7 * 60 + 30, 7 * 60 + 50]))

    # routes = {route_example.id: route_example}

    # Transfers
    # determine if walkable
    # transfers: List[Transfer] = []
    # for s1 in stops.values():
    #    for s2 in stops.values():
    #        if s1.id != s2.id:
    #            distance = helper_functions.haversine(s1.lat, s1.lon, s2.lat, s2.lon)
    #            # print(distance)
    #            if distance <= MAX_WALK_DIST:
    #                walk_time_minutes = max(
    #                    MIN_TRANSFER_TIME, ceil(distance / WALKING_SPEED)
    #                )
    #                transfers.append(Transfer(s1, s2, walk_time_minutes))

    # result = raptor_algo(
    #    stops, routes, transfers, "Greenpoint", "Observatory", 7 * 60, 5
    # )

    # print(transfers)

    # print("Earliest arrivals (mins since Monday 00:00):")
    # for sid, t in result.items():
    #    print(f"{sid}: {t}")
