import sys
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from algorithm_prototype.raptor import (
    Stop,
    Route,
    Trip,
    Transfer,
    INF,
    MIN_TRANSFER_TIME,
)


@dataclass
class DijkstraNode:
    """Represents a state in the transit network for Dijkstra's algorithm"""

    stop_id: str
    time: int
    trip_id: Optional[str] = None
    route_id: Optional[str] = None

    def __lt__(self, other):
        return self.time < other.time

    def __eq__(self, other):
        return (
            self.stop_id == other.stop_id
            and self.time == other.time
            and self.trip_id == other.trip_id
            and self.route_id == other.route_id
        )

    def __hash__(self):
        return hash((self.stop_id, self.time, self.trip_id, self.route_id))


@dataclass
class DijkstraState:
    """State information for path reconstruction"""

    node: DijkstraNode
    predecessor: Optional[DijkstraNode]
    mode: str  # 'start', 'trip', 'transfer'
    cost: int
    transfer_time: Optional[int] = None
    board_pos: Optional[int] = None
    disembark_pos: Optional[int] = None


def _reconstruct_dijkstra_path(
    states: Dict[DijkstraNode, DijkstraState],
    target_node: DijkstraNode,
    source_id: str,
    departure_time: int,
) -> List[Dict[str, Any]]:
    """Reconstruct the path from target back to source using predecessor chain.

    Traces back through the states dictionary from target to source, building
    a list of steps that represents the optimal journey. Each step contains
    information about the stop, arrival time, mode of transport, and routing details.

    Args:
        states: Dictionary mapping nodes to their state information
        target_node: The target node we reached optimally
        source_id: ID of the source stop

    Returns:
        List of path steps in chronological order (source to target)
    """
    path = []
    current_node = target_node
    visited_reconstruction = set()

    # Trace backwards from target to source
    while current_node is not None:
        # Cycle detection during reconstruction
        if current_node in visited_reconstruction:
            break
        visited_reconstruction.add(current_node)

        state = states.get(current_node)
        if state is None:
            break

        # Don't include the start state in the path steps
        if state.mode != "start":
            step = {
                "stop_id": current_node.stop_id,
                "arrival_time": current_node.time,
                "mode": state.mode,
                "route_id": current_node.route_id,
                "trip_id": current_node.trip_id,
                "transfer_time": state.transfer_time,
                "board_pos": state.board_pos,
                "disembark_pos": state.disembark_pos,
            }

            # Add predecessor information for journey continuity
            if state.predecessor:
                step["from_stop_id"] = state.predecessor.stop_id

            path.append(step)

        current_node = state.predecessor

    # Add source as starting point (only if we found a valid path)
    if path:
        path.append(
            {
                "stop_id": source_id,
                "arrival_time": departure_time,
                "mode": "start",
                "route_id": None,
                "trip_id": None,
                "transfer_time": None,
                "from_stop_id": None,
            }
        )

    # Reverse to get chronological order (source to target)
    path.reverse()
    return path


def dijkstra_algo(
    stops: Dict[str, Stop],
    routes: Dict[str, Route],
    transfers: List[Transfer],
    source_id: str,
    target_id: str,
    departure_time: int,
    max_rounds: int = 10,  # not used in Dijkstra, kept for compatibility
    debug: bool = False,
) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """Dijkstra-based public transit journey planner using standard implementation.

    Standard Dijkstra's shortest path algorithm adapted for public transit networks.
    Unlike RAPTOR which uses rounds, this explores states by increasing cost/time.
    Each state represents being at a stop at a specific time, possibly on a trip.

    Args:
        stops: Dictionary of all stops {stop_id: Stop}
        routes: Dictionary of all routes {route_id: Route}
        transfers: List of walking transfers between stops
        source_id: Starting stop ID
        target_id: Destination stop ID
        departure_time: Departure time in minutes since Monday 00:00
        max_rounds: Not used in Dijkstra, kept for interface compatibility
        debug: Enable debug output

    Returns:
        Tuple of (result_dict, path_list) compatible with raptor_algo:
        - Dict mapping stop_id to earliest arrival time
        - List of path steps for journey reconstruction
    """

    if source_id not in stops or target_id not in stops:
        return {}, []

    # Build transfer lookup for efficiency - stop_id -> [(to_stop_id, walk_time)]
    transfer_map: Dict[str, List[Tuple[str, int]]] = {}
    for t in transfers:
        if t.from_stop.id not in transfer_map:
            transfer_map[t.from_stop.id] = []
        transfer_map[t.from_stop.id].append((t.to_stop.id, t.walking_time))

    # Build route-stop mappings for efficient lookup - stop_id -> [(route_id, position)]
    stop_to_routes: Dict[str, List[Tuple[str, int]]] = {}
    for route_id, route in routes.items():
        for pos, stop in enumerate(route.stops):
            if stop.id not in stop_to_routes:
                stop_to_routes[stop.id] = []
            stop_to_routes[stop.id].append((route_id, pos))

    # Standard Dijkstra data structures
    unvisited: Dict[DijkstraNode, int] = {}  # unvisited nodes with their costs
    visited: set[DijkstraNode] = set()  # visited nodes set
    distances: Dict[DijkstraNode, int] = {}  # best known distances
    states: Dict[DijkstraNode, DijkstraState] = {}  # state info for path reconstruction

    # Result dictionary - earliest arrival at each stop (for compatibility with RAPTOR)
    result: Dict[str, int] = {stop_id: INF for stop_id in stops.keys()}

    # Initialize with source
    start_node = DijkstraNode(source_id, departure_time)
    unvisited[start_node] = departure_time
    distances[start_node] = departure_time
    result[source_id] = departure_time

    states[start_node] = DijkstraState(
        node=start_node, predecessor=None, mode="start", cost=departure_time
    )

    best_target_node: Optional[DijkstraNode] = None
    best_target_cost = INF
    iteration_count = 0

    # Main Dijkstra loop
    while unvisited:
        # Find unvisited node with minimum distance (standard Dijkstra approach)
        current_node = min(unvisited.keys(), key=lambda n: unvisited[n])
        current_cost = unvisited[current_node]

        # Remove from unvisited and add to visited
        del unvisited[current_node]
        visited.add(current_node)

        iteration_count += 1
        if debug and iteration_count % 1000 == 0:
            print(
                f"Processed {iteration_count} nodes, current: {current_node.stop_id} at {current_cost}, unvisited: {len(unvisited)}"
            )

        # Check if we've reached target
        if current_node.stop_id == target_id:
            if current_cost < best_target_cost:
                best_target_cost = current_cost
                best_target_node = current_node
                result[target_id] = current_cost
            # Continue to potentially find better paths to target

        # Early termination if we've already found optimal path to target
        if best_target_cost != INF and current_cost >= best_target_cost:
            continue

        # Explore walking transfers from current stop
        for to_stop_id, walk_time in transfer_map.get(current_node.stop_id, []):
            walk_time = max(
                walk_time, MIN_TRANSFER_TIME
            )  # enforce minimum transfer time
            new_time = current_node.time + walk_time
            new_node = DijkstraNode(to_stop_id, new_time)

            # Skip if already visited
            if new_node in visited:
                continue

            new_cost = current_cost + walk_time

            # Update if we found a better path
            if new_cost < distances.get(new_node, INF) and new_cost < result.get(
                to_stop_id, INF
            ):
                distances[new_node] = new_cost
                unvisited[new_node] = new_cost
                result[to_stop_id] = min(result[to_stop_id], new_time)

                states[new_node] = DijkstraState(
                    node=new_node,
                    predecessor=current_node,
                    mode="transfer",
                    cost=new_cost,
                    transfer_time=walk_time,
                )

        # Explore boarding vehicles at current stop
        for route_id, stop_pos in stop_to_routes.get(current_node.stop_id, []):
            route = routes[route_id]

            # Try each trip on this route
            for trip in route.trips:
                # Check if we can board this trip at this stop
                board_time = trip.departure_times[stop_pos]
                if board_time == INF or board_time < current_node.time:
                    continue  # can't board this trip - already departed or invalid time

                # Explore all subsequent stops on this trip
                for next_pos in range(stop_pos + 1, len(route.stops)):
                    arrival_time = trip.departure_times[next_pos]
                    if arrival_time == INF or arrival_time <= board_time:
                        continue  # invalid or backward time on trip

                    next_stop = route.stops[next_pos]
                    trip_node = DijkstraNode(
                        next_stop.id, arrival_time, trip.id, route_id
                    )

                    # Skip if already visited
                    if trip_node in visited:
                        continue

                    # Cost is the arrival time (minimize arrival time)
                    new_cost = arrival_time

                    # Update if we found a better path
                    if new_cost < distances.get(
                        trip_node, INF
                    ) and new_cost < result.get(next_stop.id, INF):

                        distances[trip_node] = new_cost
                        unvisited[trip_node] = new_cost
                        result[next_stop.id] = min(result[next_stop.id], arrival_time)

                        states[trip_node] = DijkstraState(
                            node=trip_node,
                            predecessor=current_node,
                            mode="trip",
                            cost=new_cost,
                            board_pos=stop_pos,
                            disembark_pos=next_pos,
                        )

    # Reconstruct path from target back to source
    path = []
    if best_target_node is not None:
        path = _reconstruct_dijkstra_path(
            states, best_target_node, source_id=source_id, departure_time=departure_time
        )

    return result, path
