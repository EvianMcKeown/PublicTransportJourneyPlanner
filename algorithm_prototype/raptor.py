### version 1
# import multiprocessing as mp
from dataclasses import dataclass, field
from email.policy import default
from hmac import new
from os import name, walk
import queue
from re import I
import sys
from tracemalloc import stop
from typing import Any, List, Dict, Literal, Optional, Tuple
from math import ceil, radians, cos, sin, asin, sqrt
from rtree import index

# Haversine formula

# Value used as INFINITY
INF: int = sys.maxsize
MAX_WALK_DIST = 1000  # maximum walkable distance in meters
WALKING_SPEED = 5 * 1000 / 60  # meters oer minute
MIN_TRANSFER_TIME = 1  # mins
EARTH_RADIUS_KM = 6371.0  # Standard Earth radius
METERS_PER_DEG_LAT = 111111  # Approx. meters per degree lat


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
    def parse_time_mins(time_str: str) -> int | Literal["VIA"]:
        if not time_str or time_str.strip() == "" or time_str.strip().upper() == "N/A":
            return INF
        if time_str.strip().upper() == "VIA":
            return "VIA"  # Special marker, will be handled later
        try:
            h, m, s = map(int, time_str.strip().split(":"))
            return h * 60 + m
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")

    @staticmethod
    def _estimate_via_times(times: List[int], is_via: List[bool]) -> List[int]:
        """
        Replace times marked by is_via associated with a trip,
        with estimated values based on nearest non-INF neighbors (skipping INF).

        Args:
            times (List[int]): List of times (int incl. INF).
            is_via (List[bool]): List indicating positions of 'VIA' markers.

        Returns:
            List[int]: List with 'VIA' replaced by estimated times.
        """

        estimated_times = list(times)
        num_times = len(estimated_times)
        idx = 0
        while idx < num_times:
            if not is_via[idx]:
                idx += 1
                continue

            # Find continuous segment of VIA
            segment_start = idx
            segment_end = idx
            while segment_end < num_times and is_via[segment_end]:
                segment_end += 1

            # Find left non-INF neighbor
            left_idx = segment_start - 1
            while left_idx >= 0 and estimated_times[left_idx] == INF:
                left_idx -= 1

            # Find right non-INF neighbor
            right_idx = segment_end
            while right_idx < num_times and estimated_times[right_idx] == INF:
                right_idx += 1

            # Interpolate if both neighbors found
            if (
                left_idx >= 0
                and right_idx < num_times
                and estimated_times[left_idx] != INF
                and estimated_times[right_idx] != INF
            ):
                start_time = estimated_times[left_idx]
                end_time = estimated_times[right_idx]
                while end_time < start_time:
                    end_time += 24 * 60  # Adjust for next day
                gap_size = right_idx - left_idx - 1
                for offset in range(1, gap_size + 1):
                    pos = left_idx + offset
                    if is_via[pos]:
                        estimated_times[pos] = int(
                            start_time
                            + (end_time - start_time) * offset / (gap_size + 1)
                        )
            # move past VIA segment
            idx = segment_end
        return estimated_times

    @staticmethod
    def _check_trip_times(times: List[int]) -> Tuple[bool, int]:
        """Check if trip times are non-decreasing, ignoring INF values.

        Args:
            times (List[int]): List of times (int or INF).
        Returns:
            bool: True if non-decreasing, False otherwise.
        """
        last_time = -1
        for i, t in enumerate(times):
            if t != INF:
                if last_time == -1:
                    last_time = t
                    continue
                if t < last_time:
                    return False, i
                    raise ValueError("Trip times must be non-decreasing.")
                    return False
                last_time = t
        return True, -1

    @staticmethod
    def create_transfers(
        stops: Dict[str, Stop],
        max_walking_dist: int = MAX_WALK_DIST,
        min_transfer_time: int = MIN_TRANSFER_TIME,
        walking_speed: float = WALKING_SPEED,
    ) -> List[Transfer]:
        """Creates transfers between all stops that are walkable within the specified maximum walking distance.
        Use R-tree pre-filter for efficiency (O(n log n))

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
        stop_list = list(stops.values())

        # build r-tree index
        p = index.Property()
        idx = index.Index(properties=p)
        # insert all stops into R-tree
        # bounds for each stop are its (lat, lon) repeated
        for id, stop in enumerate(stop_list):
            idx.insert(id, (stop.lon, stop.lat, stop.lon, stop.lat))

        # perform filtered search
        degree_offset = (
            max_walking_dist / METERS_PER_DEG_LAT
        )  # simplified bounding degree distance
        for s1 in stop_list:
            # define bounding box centered at s1
            # (min_lon, min_lat, max_lon, max_lat)
            bounding_box = (
                s1.lon - degree_offset,
                s1.lat - degree_offset,
                s1.lon + degree_offset,
                s1.lon + degree_offset,
            )

            candidate_indices = idx.intersection(bounding_box)

            # refine with haversine distance
            for s2_index in candidate_indices:
                s2 = stop_list[s2_index]  # get obj
                if s1.id == s2.id:
                    # skip if s1 == s2
                    continue
                # perform haversine only on pre-filtered set of stops
                distance = helper_functions.haversine(s1.lat, s1.lon, s2.lat, s2.lon)

                if distance <= max_walking_dist:
                    walk_time_minutes = max(
                        min_transfer_time,
                        ceil(distance / walking_speed),  # meters per minute
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

    @staticmethod
    def detect_local_cycle(
        current_idx: int,
        prev_idx: int,
        predecessor: List[Optional[Dict]],
        max_steps: int = 128,
    ) -> bool:
        """
        Walk the predecessor chain from prev_idx; if we reach current_idx, a cycle would be formed.
        Bounded to max_steps for safety.
        """
        steps = 0
        cur = prev_idx
        while steps < max_steps and cur is not None and predecessor[cur] is not None:
            if cur == current_idx:
                return True
            if predecessor[cur] is None:
                break
            cur = predecessor[cur]["prev_idx"]
            steps += 1
        return False

    @staticmethod
    def safe_set_predecessor(
        current_idx: int,
        prev_idx: int,
        arrival_time: int,
        mode: str,
        route_id: Optional[str],
        trip_id: Optional[str],
        transfer_time: Optional[int],
        predecessor: List[Optional[Dict]],
        idx_to_id: Dict[int, str],
        debug: bool = False,
    ) -> bool:
        """
        Guarded predecessor update. Returns True if set, False if skipped.

        Avoids:
            - 2-cycles (prev -> current while current -> prev)
            - longer cycles detected via bounded walk
        """

        # Prevent: 2-cycle
        pred_prev = predecessor[prev_idx]
        if pred_prev is not None and pred_prev.get("prev_idx") == current_idx:
            if debug:
                # raise ValueError(
                #    f"2-cycle avoided: {idx_to_id.get(prev_idx)} <-> {idx_to_id.get(current_idx)} "
                #    f"(mode={mode}, route={route_id}, trip={trip_id})"
                # )
                # Log instead of raising; skip update
                raise ValueError(
                    f"[safe_set_predecessor] 2-cycle skipped: "
                    f"{idx_to_id.get(prev_idx)} <-> {idx_to_id.get(current_idx)} "
                    f"(mode={mode}, route={route_id}, trip={trip_id}, t={arrival_time})"
                )
            return False

        # Prevent: longer cycle
        if helper_functions.detect_local_cycle(current_idx, prev_idx, predecessor):
            if debug:
                # raise ValueError(
                #    f"Cycle avoided while setting predecessor for {idx_to_id.get(current_idx)} "
                #    f"from {idx_to_id.get(prev_idx)} (mode={mode}, route={route_id}, trip={trip_id})"
                # )
                # Log instead of raising; skip update
                raise ValueError(
                    f"[safe_set_predecessor] 2-cycle skipped: "
                    f"{idx_to_id.get(prev_idx)} <-> {idx_to_id.get(current_idx)} "
                    f"(mode={mode}, route={route_id}, trip={trip_id}, t={arrival_time})"
                )
            return False

        predecessor[current_idx] = {
            "prev_idx": prev_idx,
            "arrival_time": arrival_time,
            "mode": mode,
            "route_id": route_id,
            "trip_id": trip_id,
            "transfer_time": transfer_time,
        }
        return True


def raptor_algo(
    stops: Dict[str, Stop],
    routes: Dict[str, Route],
    transfers: List[Transfer],
    source_id: str,
    target_id: str,
    departure_time: int,
    max_rounds: int = 10,
    debug: bool = True,
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

    check_transfer_loops(transfers)  # check no self loops in transfers

    if debug:
        # detect accidental duplicates or bad trip times before running
        for r in routes.values():
            for t in r.trips:
                try:
                    helper_functions._check_trip_times(t.departure_times)
                except ValueError as e:
                    raise ValueError(
                        f"In route_id '{r.id}', trip_id '{t.id}': {e}"
                    ) from e

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

    target_idx: Optional[int] = id_to_idx[target_id] if target_id in id_to_idx else None

    # earliest arrival time for each stop over all rounds
    best = [INF] * n
    prev = [INF] * n
    cur = [INF] * n

    # initialise
    if source_id not in id_to_idx:
        raise ValueError("Origin not a valid Stop.")
    source_idx = id_to_idx[source_id]

    # store predecessors for path reconstruction
    # each entry is a dict per round with keys: prev_idx, arrival_time, mode, route_id, trip_id, transfer_time
    # or None if no predecessor (initially)
    predecessor_layers: List[List[Optional[Dict]]] = [
        [None] * n for _ in range(max_rounds + 1)
    ]
    improved_round: List[int] = [-1] * n  # last round a stop was improved

    best[source_idx] = departure_time
    prev[source_idx] = departure_time
    cur[source_idx] = departure_time
    # ↓ source known at round 0 ↓
    improved_round[source_idx] = 0
    predecessor_layers[0][source_idx] = None

    # marked stops: those improved in the last round (init to only source)
    marked = [False] * n
    marked[source_idx] = True
    marked_list = [source_idx]

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
                    # skip invalid/missing times
                    if trip_departure == INF:
                        continue
                    if trip_departure >= arr_prev:
                        boarded_at = pos
                        break  # board at first possible stop, and stop checking

                if boarded_at is None:
                    # can't use this trip from any marked stop
                    continue

                # stop where we boarded
                board_stop_idx = stop_indices[boarded_at]
                board_time = trip.departure_times[boarded_at]

                # move along trip from boarded_at stop
                # -> start look form stop after the boarding_at stop
                for pos2 in range(boarded_at + 1, num_stops_in_route):
                    stop_idx2 = stop_indices[pos2]
                    # arrival time at stop_idx2
                    trip_time = trip.departure_times[pos2]
                    if trip_time == INF:
                        continue  # don't propagate invalid times
                    prev_stop_idx = stop_indices[pos2 - 1]

                    # skip backward in time segments in the same trip
                    prev_time_same_trip = trip.departure_times[pos2 - 1]
                    if prev_time_same_trip != INF and trip_time < prev_time_same_trip:
                        continue

                    # NEW: enforce time >= boarding time to avoid drops after INF gaps/misalignment
                    if trip_time < board_time:
                        continue

                    # commit only if both this round and overall best improved
                    if trip_time < cur[stop_idx2] and trip_time < best[stop_idx2]:
                        if stop_idx2 == source_idx and trip_time > departure_time:
                            # Don't overwrite source with later time
                            continue

                        # predecessor is the boarding stop (not the immediate previous stop)
                        if helper_functions.safe_set_predecessor(
                            stop_idx2,
                            board_stop_idx,
                            trip_time,
                            "trip",
                            rid,
                            trip.id,
                            None,
                            predecessor_layers[k],  # write to this rounds layer
                            idx_to_id,
                            debug,
                        ):
                            # add boarding metadata to help reconstruction
                            # TODO: handle predecessor_layers being None
                            predecessor_layers[k][stop_idx2]["board_pos"] = boarded_at
                            predecessor_layers[k][stop_idx2]["disembark_pos"] = pos2
                            predecessor_layers[k][stop_idx2]["round"] = k
                            predecessor_layers[k][stop_idx2]["prev_round"] = k - 1

                            # update times
                            cur[stop_idx2] = trip_time
                            # best[stop_idx2] = min(best[stop_idx2], trip_time)
                            best[stop_idx2] = trip_time
                            # mark which round a stop was last improved
                            improved_round[stop_idx2] = k

                            if not marked[stop_idx2]:
                                marked[stop_idx2] = True
                                marked_list.append(stop_idx2)
                                improved = True

                            # debug: early cycle check when target reached
                            if (
                                debug
                                and target_idx is not None
                                and best[target_idx] != INF
                            ):
                                check_predecessor_cycles(
                                    predecessor_layers[k],
                                    idx_to_id,
                                    target_idx,
                                    source_idx,
                                )

        # 3: Look at foot-paths (transfers) — since we have no chained walks and
        # we are using a fixed distance based formula for walking time, all we
        # have to do is 'walk' through (pardon the pun) each transfer.
        marked_list_copy = list(marked_list)  # avoid modification during iteration
        for p in marked_list_copy:
            arr_p = cur[p]
            if arr_p == INF:
                continue

            for v, walk_time in transfer_adj[p]:
                # enforce strictly positive transfer time
                walk_time = max(walk_time, MIN_TRANSFER_TIME)
                new_arrival = arr_p + walk_time

                if new_arrival < cur[v] and new_arrival < best[v]:
                    if helper_functions.safe_set_predecessor(
                        v,
                        p,
                        new_arrival,
                        "transfer",
                        None,
                        None,
                        walk_time,
                        predecessor_layers[k],  # write to this round's layer
                        idx_to_id,
                        debug,
                    ):
                        predecessor_layers[k][v]["round"] = k
                        predecessor_layers[k][v][
                            "prev_round"
                        ] = k  # transfers stay in same round
                        cur[v] = new_arrival
                        best[v] = new_arrival
                        improved_round[v] = (
                            k  # mark which round a stop was last improved
                        )

                        # transfers can mark a stop not reached by a trip
                        if not marked[v]:
                            marked[v] = True
                            marked_list.append(v)
                            improved = True

                        if debug and target_idx is not None and best[target_idx] != INF:
                            # debug: early cycle check when target reached
                            check_predecessor_cycles(
                                predecessor_layers[k], idx_to_id, target_idx, source_idx
                            )

                    # Optional: early cycle check once the target is reachable in this round
                    # if target_id in id_to_idx:
                    #    tidx = id_to_idx[target_id]
                    #    if best[tidx] != INF:
                    #        check_predecessor_cycles(
                    #            predecessor, idx_to_id, tidx, source_idx
                    #        )

        prev = cur[:]  # shallow copy list (values, not references)
        cur = [INF] * n
        if not improved:
            break

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

    # final cycle check before reconstructing path
    # check_self_loops(predecessor, idx_to_id)
    # check_predecessor_cycles(predecessor, idx_to_id, target_idx, source_idx)

    journey = reconstruct_path(
        predecessor_layers, improved_round, idx_to_id, target_idx, source_idx, result
    )

    return result, journey


def reconstruct_path(
    predecessor_layers: List[List[Optional[Dict]]],
    improved_round: List[int],
    idx_to_id: Dict[int, str],
    target_idx: int,
    source_idx: int,
    result: Dict[str, int],
) -> List[Dict[str, Any]]:
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
    path: List[Dict[str, Any]] = []
    # prev_2 = None
    # prev = None
    current = target_idx
    visited = set()  # to detect cycles

    # start from the round where target was last improved
    r = improved_round[target_idx]
    if r < 0:
        return []  # no path found

    # trace from target back to source
    while current != source_idx:
        pred = (
            predecessor_layers[r][current] if 0 <= r < len(predecessor_layers) else None
        )
        if pred is None:
            return []  # no predecessor found (shouldn't happen due to earlier checks)

        key = (current, r)
        if key in visited:
            # cycle detected
            raise ValueError(
                f"Cycle detected during path reconstruction at stop {idx_to_id[current]} in round {r}."
            )
        visited.add(key)

        step = dict(pred)  # copy to avoid mutating original
        step["stop_id"] = idx_to_id[current]
        step["from_stop_id"] = idx_to_id[step["prev_idx"]]
        path.append(step)
        # prev_2 = prev
        # prev = current

        next_idx = step.get("prev_idx")
        next_round = step.get("prev_round", r - 1 if step.get("mode") == "trip" else r)

        current = next_idx
        r = next_round

    # If the trace stops before the source, something went wrong, or the source
    # was reached via a transfer that wasn't recorded properly (which is unlikely
    # for the initial source stop). We rely on the initial check for path existence.
    # if current != source_idx:
    #     empty_path: List[Dict] = []
    #     return empty_path

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


def check_duplicate_stops(route: Route):
    seen = set()
    for stop in route.stops:
        if stop.id in seen:
            raise ValueError(f"Duplicate stop {stop.id} found in route {route.id}")
        seen.add(stop.id)


def check_self_loops(predecessor: List[Optional[Dict]], idx_to_id: Dict[int, str]):
    for idx, pred in enumerate(predecessor):
        if pred is not None and pred["prev_idx"] == idx:
            stop_id = idx_to_id[idx]
            raise ValueError(f"Self-loop detected at stop {stop_id}")


def check_predecessor_cycles(
    predecessor: List[Optional[Dict]],
    idx_to_id: Dict[int, str],
    target_idx: int,
    source_idx: int,
):
    visited = set()
    prev_2 = None
    prev = None
    current = target_idx
    while current != source_idx and predecessor[current] is not None:
        if current in visited:
            stop_id = idx_to_id[current]
            raise ValueError(
                f"Cycle detected in predecessor chain at stop {stop_id}. "
                f"prev: {idx_to_id[prev] if prev is not None else 'None'}, prev_2: {idx_to_id[prev_2] if prev_2 is not None else 'None'}"
            )
        visited.add(current)
        prev_2 = prev
        prev = current
        if predecessor[current] is None:
            break
        current = predecessor[current]["prev_idx"]
    return False


def check_transfer_loops(transfers: List[Transfer]):
    for t in transfers:
        if t.from_stop.id == t.to_stop.id:
            raise ValueError(f"Transfer loop detected at stop {t.from_stop.id}")


def align_trip_times(canonical_stop_ids, trip_stop_ids, trip_times):
    """
    Align trip times to canonical stop sequence, filling with INF where stops are missing.

    Args:
        canonical_stop_ids (List[str]): The canonical sequence of stop IDs.
        trip_stop_ids (List[str]): The stop IDs for a specific trip.
        trip_times (List[int]): The corresponding times for the trip's stops.
    Returns:
        List[int]: Aligned times with INF for missing stops.
    """
    aligned_times = []
    trip_idx = 0
    for canon_stop_id in canonical_stop_ids:
        # find next occurrence of canon_stop_id in trip_stop_ids
        while (
            trip_idx < len(trip_stop_ids) and trip_stop_ids[trip_idx] != canon_stop_id
        ):
            trip_idx += 1
        if trip_idx < len(trip_stop_ids):
            aligned_times.append(trip_times[trip_idx])
        else:
            aligned_times.append(INF)
    return aligned_times


def reconstruct_path_objs(
    path: List[Dict[str, Any]],
    stops_dict: Dict[str, "Stop"],
    routes_dict: Dict[str, "Route"],
    transfers_dict: Dict[Tuple[str, str], Transfer],
) -> List[Dict[str, Any]]:
    """
    Convert the ID-based path returned by raptor_algo into a path enriched with
    Stop/Route/Trip/Transfer objects. For trip steps, boarding/disembark stops
    are derived from board_pos and disembark_pos (indices into route.stops).

    Args:
        path (List[Dict[str, Any]]): Path returned by RAPTOR with stop and route IDs.
        stops_dict (Dict[str, Stop]): Dictionary of all Stop objects by ID.
        routes_dict (Dict[str, Route]): Dictionary of all Route objects by ID.

    Returns:
        List[Dict[str, Any]]: Path with Stop, Route, Trip, and Transfer object references.


    """
    path_objs: List[Dict[str, Any]] = []

    for step in path:
        new_step = dict(step)  # shallow copy

        stop_id = new_step.get("stop_id")
        from_stop_id = new_step.get("from_stop_id")

        if stop_id in stops_dict:
            new_step["stop_object"] = stops_dict[stop_id]
        if from_stop_id in stops_dict:
            new_step["from_stop_object"] = stops_dict[from_stop_id]

        mode = new_step.get("mode")

        if mode == "trip":
            rid = new_step.get("route_id")
            tid = new_step.get("trip_id")
            route = routes_dict.get(rid)
            if route is not None:
                new_step["route_object"] = route
                if tid:
                    trip_obj = next((t for t in route.trips if t.id == tid), None)
                    if trip_obj is not None:
                        new_step["trip_object"] = trip_obj

                # Use board_pos / disembark_pos to resolve boarding/disembark stops
                board_pos = new_step.get("board_pos")
                disembark_pos = new_step.get("disembark_pos")

                if isinstance(board_pos, int) and 0 <= board_pos < len(route.stops):
                    board_stop_obj = route.stops[board_pos]
                    new_step["board_stop_object"] = board_stop_obj
                    new_step["board_stop_id"] = board_stop_obj.id
                else:
                    # fallback: from_stop_id
                    if from_stop_id in stops_dict:
                        new_step["board_stop_object"] = stops_dict[from_stop_id]
                        new_step["board_stop_id"] = from_stop_id

                if isinstance(disembark_pos, int) and 0 <= disembark_pos < len(
                    route.stops
                ):
                    disembark_stop_obj = route.stops[disembark_pos]
                    new_step["disembark_stop_object"] = disembark_stop_obj
                    new_step["disembark_stop_id"] = disembark_stop_obj.id
                else:
                    # fallback: stop_id
                    if stop_id in stops_dict:
                        new_step["disembark_stop_object"] = stops_dict[stop_id]
                        new_step["disembark_stop_id"] = stop_id

        elif mode == "transfer":
            if from_stop_id and stop_id:
                tr_key = (from_stop_id, stop_id)
                tr_obj = transfers_dict.get(tr_key)
                if tr_obj is not None:
                    new_step["transfer_object"] = tr_obj
                    new_step.setdefault("transfer_time", tr_obj.walking_time)

        path_objs.append(new_step)

    return path_objs
