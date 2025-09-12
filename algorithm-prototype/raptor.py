### version 1
# import multiprocessing as mp
from dataclasses import dataclass
import sys
from typing import List, Dict, Tuple

# Value used as INFINITY
INF: int = sys.maxsize


@dataclass
class Stop:
    """each stop corresponds to a distinct location,
    where a commuter can board or get off a vehicle (train, bus, etc.)"""

    id: int
    mode: int  # 1=train, 2=myciti, ...


@dataclass
class Trip:
    """a sequence of stops a specific vehicle (train, bus, etc.)
    makes on a line (route) - at each stop it may pick up or drop-off passengers
    """

    stops: List[Stop]
    departures: List[int]  # departure times aligned with stops
    arrivals: List[int]  # arrival times aligned with stops

    @property
    def mode(self) -> int:
        return self.stops[0].mode if self.stops else -1


@dataclass
class Route:
    """ordered list of stops and the trips coinciding with them
    TODO maybe make a single list contain all this for a DOD approach?"""

    id: int
    stops: List[
        Stop
    ]  # can remove duplication of stops between routes and trips later
    trips: List[Trip]

    def add_trip(self, trip: Trip):
        self.trips.append(trip)


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
    # initailise earliest know arrival time at p with up to i trips to inf
    # for i in stops:
    #    pass
    # then we set earliest know arrival time at the source stop with 0 trips equal to the departure time

    return {0: 0}


if __name__ == "__main__":
    source = Stop(0, 1)
    destination = Stop(1, 1)
    start_time = 10

    example_list_stops = [Stop(0, 1), Stop(1, 1)]
    example_departures = [15, 30]
    example_arrivals = [10, 25]

    example_route: List[Route] = [
        Route(
            0,
            example_list_stops,
            [Trip(example_list_stops, example_departures, example_arrivals)],
        )
    ]

    raptor_algo(source, destination, start_time, example_route)


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
