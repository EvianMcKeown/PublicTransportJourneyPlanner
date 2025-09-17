### version 1
# import multiprocessing as mp
from dataclasses import dataclass
from re import I
import sys
from typing import List, Dict, Optional, Tuple
from math import radians, cos, sin, asin, sqrt  # Haversine formula

# Value used as INFINITY
INF: int = sys.maxsize


@dataclass
class Stop:
    """each stop corresponds to a distinct location,
    where a commuter can board or get off a vehicle (train, bus, etc.)"""

    id: str
    mode: int  # 1=train, 2=MyCiti, ...
    lat: float
    lon: float

    earliest_arrival: Dict[int, int] = {}  # round -> time
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
    trips: List[Trip] = []

    @property
    def mode(self) -> int:
        return self.stops[0].mode if self.stops else -1

    def add_trip(self, trip: Trip):
        # Ensure trip matches stop count
        # TODO check that no duplicate trips
        assert len(trip.departure_times) == len(self.stops)
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
        """Return distance in meters between two coordinates using Haversine formula with mean earth radius.
            Haversine formula - https://en.wikipedia.org/wiki/Haversine_formula

        Args:
            lat_a (float): latitude of coordinate a
            lon_a (float): longitude of coordinate a
            lat_b (float): latitude of coordinate b
            lon_b (float): longitude of coordinate b

        Returns:
            float: distance in meters
        """

        # degree to radian
        lat_a, lon_a, lat_b, lon_b = map(radians, [lat_a, lon_a, lat_b, lon_b])
        # get deltas
        delta_lat = lat_a - lat_b  # y
        delta_lon = lon_a - lon_b  # x
        a = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
        b = 2 * 2371 * 1000 * asin(sqrt(a))  # meters

        return b

    @staticmethod
    def walkable(
        lat_a: float, lon_a: float, lat_b: float, lon_b: float, dist=500
    ) -> bool:
        """
        Determines if two positions, a and b, are less than some maximum distance from each other.
        If so, then they can be used to move from one route to another.

        Args:
            lat_a (float): latitude of coordinate a
            lon_a (float): longitude of coordinate a
            lat_b (float): latitude of coordinate b
            lon_b (float): longitude of coordinate b
            dist (int): maximum walking distance in meters

        Returns:
            boolean: walkable
        """

        # Haversine formula - https://en.wikipedia.org/wiki/Haversine_formula

        return helper_functions.haversine(lat_a, lon_a, lat_b, lon_b) <= dist


def raptor_algo(
    stops: Dict[str, Stop],
    routes: Dict[str, Route],
    transfers: List[Transfer],
    source_id: str,
    target_id: str,
    departure_time: int,
    max_rounds: int = 10,
) -> Dict[str, [int]]:
    """RAPTOR - Round bAsed Public Transit Optimised Router.

    v1: unoptimised

    Args:
        TODO

    Returns:
        TODO
    """

    # build index mapping for array storage
    stop_ids = list(stops.keys())
    id_to_idx: Dict[str, int] = {sid: i for i, sid in enumerate(stop_ids)}
    idx_to_id: Dict[int, str] = {i: sid for sid, i in id_to_idx.items()}
    n = len(stops.keys())

    # adjacency lists for transfers (indices) - walking time from stop u to v
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
    source__idx

    # set source stop earliest-arrival time to departure time
    stops.update()


if __name__ == "__main__":

    # Example Stops
    a = Stop("Greenpoint", 2, -33.918, 18.423)
    b = Stop("Gardens", 2, -33.935, 18.413)
    c = Stop("Observatory", 2, -34.05, 18.35)

    stops = {s.id: s for s in [a, b, c]}
    # stops = [a, b, c]

    # Example Routes
    route_example = Route("A", [a, b, c])
    route_example.add_trip(Trip("A-1", [7 * 60, 7 * 60 + 10, 7 * 60 + 30]))
    route_example.add_trip(Trip("A-2", [7 * 60, 7 * 60 + 10, 7 * 60 + 30]))

    routes = {route_example.id: route_example}

    # Transfers
    # determine if walkable
    transfers = []
    for s1 in stops.values():
        for s2 in stops.values():
            if helper_functions.walkable(s1.lat, s1.lon, s2.lat, s1.lon, 5000):
                transfers.append(Transfer(s1, s2, 10))
                # TODO calculate time to walk by Haversine

    raptor_algo()
