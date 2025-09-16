### version 1
# import multiprocessing as mp
from dataclasses import dataclass
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
    def check_dep_arr_times(departure_time: int, arrival_time: int) -> bool:
        return True if (arrival_time <= departure_time) else False

    @staticmethod
    def stops_same_mode(stops) -> bool:
        return True

    @staticmethod
    def walkable(
        lat_a: float, lon_a: float, lat_b: float, lon_b: float, dist=500
    ) -> bool:
        """
        Determines if two positions, a and b, are less than some maximum distance from each other.
        If so, then they can be used to move from one route to another.

        :param a_lat: latitude of position a
        :type a_lat: float
        :param a_lon: longitude of position a
        :type a_lon: float
        :param b_lat: latitude of position b
        :type b_lat: float
        :param b_lon: longitude of position b
        :type b_lon: float
        :return: If the positions are walkable - return True. Otherwise, return False.
        :rtype: bool
        """

        # Haversine formula - https://en.wikipedia.org/wiki/Haversine_formula

        # degree to radian
        lat_a, lon_a, lat_b, lon_b = map(radians, [lat_a, lon_a, lat_b, lon_b])
        # get deltas
        delta_lat = lat_a - lat_b  # y
        delta_lon = lon_a - lon_b  # x
        a = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
        b = 2 * 2367 * 1000 * asin(sqrt(a))  # meters

        return True if b <= dist else False


def raptor_algo(
    source: Stop,
    destination: Stop,
    departure_time: int,
    routes: List[Route],
    max_rounds: int = 10,
) -> Dict[int, int]:
    """Compute earliest arrival times using RAPTOR - Round bAsed Public Transit Optimised Router.

    Args:
        source (Stop): origin Stop
        destination (Stop): destination Stop
        departure_time (int): starting time in seconds
        routes (List[Route]): list of Route objects - where each Route is an ordered list of stops and the trips coinciding with them.
        max_rounds (int, optional): maximum rounds to compute. Defaults to 10.

    Returns:
        TODO
    """

    # DOD: routes = [[num_trips, num_stops, [stop0, stop1, ..., stop_k], [trip0, trip1, ..., trip_k]], ...]

    num_stops: int = max(s.id for r in routes for s in r.stops) + 1

    # labels to track best know arrival time at each stop
    best = [INF] * num_stops
    print(best)

    # route_
    # earliest_arrival[i][p]
    # initialise earliest known arrival time at p with up to i trips to inf
    # for i in stops:
    #    pass
    # then we set earliest know arrival time at the source stop with 0 trips equal to the departure time

    return {0: 0}


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
