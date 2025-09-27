from algorithm_prototype import raptor
from algorithm_prototype.raptor import (
    Stop,
    Route,
    Trip,
    Transfer,
    raptor_algo,
    helper_functions as hf,
    reconstruct_path_objs,
    check_duplicate_stops,
    check_transfer_loops,
    check_self_loops,
    check_predecessor_cycles,
)
from algorithm_prototype.gtfs_reader import GTFSReader
from datetime import timedelta

# import pytest


def test_simple_route():
    a = Stop("A", 2, -33.918, 18.423)
    b = Stop("B", 2, -33.935, 18.413)
    c = Stop("C", 2, -34.05, 18.35)

    stops_dict = {s.id: s for s in [a, b, c]}  # define stops dictionary
    stops = [a, b, c]

    route = Route("R1", stops, [])
    trip_1 = Trip("T1", [420, 430, 450])  # 420 = 7:00, 430 = 7:10, 450 = 7:30
    route.add_trip(trip_1)
    routes = {route.id: route}
    transfers = []

    # check for duplicate stops in route
    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    arrival_times, path = raptor_algo(stops_dict, routes, transfers, "A", "C", 410, 5)
    assert arrival_times["A"] == 410
    assert arrival_times["B"] == 430
    assert arrival_times["C"] == 450


def test_route_with_simple_transfer():
    # Create stops
    a = Stop("A", 2, -33.918, 18.423)
    b = Stop("B", 2, -33.935, 18.413)
    c = Stop("C", 2, -34.05, 18.35)
    d = Stop("D", 2, -34.06, 18.36)

    stops_dict = {s.id: s for s in [a, b, c, d]}

    # Route 1: A -> B
    route1 = Route("R1", [a, b], [])
    route1.add_trip(Trip("T1", [420, 430]))  # 7:00, 7:10

    # Route 2: C -> D
    route2 = Route("R2", [c, d], [])
    route2.add_trip(Trip("T2", [440, 450]))  # 7:20, 7:30

    routes = {route1.id: route1, route2.id: route2}

    # Transfer: B -> C (takes 5 minutes)
    transfers = [Transfer(b, c, 5)]

    # check for duplicate stops in route
    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from A to D, starting at 7:00 (420)
    arrival_times, path = raptor_algo(stops_dict, routes, transfers, "A", "D", 420, 5)

    # Expected: A=420, B=430, C=435 (B->C transfer), D=450 (on trip T2)
    assert arrival_times["A"] == 420
    assert arrival_times["B"] == 430
    assert arrival_times["C"] == 435
    assert arrival_times["D"] == 450


def test_transfer_time_edge_case():
    # Create stops
    a = Stop("A", 2, -33.918, 18.423)
    b = Stop("B", 2, -33.935, 18.413)
    c = Stop("C", 2, -34.05, 18.35)
    d = Stop("D", 2, -34.06, 18.36)

    stops_dict = {s.id: s for s in [a, b, c, d]}

    # Route 1: A -> B
    route1 = Route("R1", [a, b], [])
    route1.add_trip(Trip("T1", [420, 430]))  # 7:00, 7:10

    # Route 2: C -> D
    route2 = Route("R2", [c, d], [])
    route2.add_trip(Trip("T2", [435, 445]))  # 7:15, 7:25

    routes = {route1.id: route1, route2.id: route2}

    # Transfer: B -> C (takes exactly 5 minutes)
    transfers = [Transfer(b, c, 5)]

    # check for duplicate stops in route
    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from A to D, starting at 7:00 (420)
    arrival_times, path = raptor_algo(stops_dict, routes, transfers, "A", "D", 420, 5)

    # Expected: A=420, B=430, C=435 (B->C transfer), D=445 (on trip T2)
    assert arrival_times["A"] == 420
    assert arrival_times["B"] == 430
    assert arrival_times["C"] == 435
    assert arrival_times["D"] == 445


def test_multiple_competing_routes():
    # Create stops
    a = Stop("A", 2, -33.918, 18.423)
    b = Stop("B", 2, -33.935, 18.413)
    c = Stop("C", 2, -34.05, 18.35)
    d = Stop("D", 2, -34.06, 18.36)
    e = Stop("E", 2, -34.07, 18.37)

    stops_dict = {s.id: s for s in [a, b, c, d, e]}

    # Route 1 (R1): A -> B -> C (fast but less frequent)
    route1 = Route("R1", [a, b, c], [])
    route1.add_trip(Trip("T1", [420, 430, 440]))  # 7:00, 7:10, 7:20

    # Route 2 (R2): A -> D -> E (slower but more frequent)
    route2 = Route("R2", [a, d, e], [])
    route2.add_trip(Trip("T2", [420, 435, 450]))  # 7:00, 7:15, 7:30
    route2.add_trip(Trip("T3", [430, 445, 500]))  # 7:10, 7:25, 7:40

    routes = {route1.id: route1, route2.id: route2}

    # Transfers from B and D to the destination E (takes 5 minutes)
    transfers = [Transfer(b, e, 5), Transfer(d, e, 5)]

    # check for duplicate stops in route
    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from A to E, starting at 7:00 (420)
    arrival_times, path = raptor_algo(stops_dict, routes, transfers, "A", "E", 420, 5)

    # Expected fastest path: A(420) -> B(430) -> Transfer -> E(435)
    # The alternative path A(420) -> D(435) -> E(440) is slower.
    assert arrival_times["A"] == 420
    assert arrival_times["B"] == 430
    assert arrival_times["E"] == 435
    # assert path["E"][0].stop_id == "B" # Path must arrive from B


def test_simple_path_reconstruction():
    """
    Tests the path reconstruction for a single, direct trip (A -> B).
    Verifies the structure and content of the returned path list.
    """
    # Create stops
    a = Stop("SA", 1, -34.0, 18.0, name="Stop A")
    b = Stop("SB", 1, -34.1, 18.1, name="Stop B")

    stops_dict = {s.id: s for s in [a, b]}

    # Route R1: SA -> SB
    route1 = Route("R1", [a, b], [])
    trip_1 = Trip(
        "T101", [420, 435]
    )  # Departs A at 7:00 (420), Arrives B at 7:15 (435)
    route1.add_trip(trip_1)

    routes = {route1.id: route1}
    transfers = []

    start_time = 415  # 6:55 AM (early enough to catch the 7:00 trip)

    # check for duplicate stops in route
    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from SA to SB
    arrival_times, path = raptor_algo(
        stops_dict, routes, transfers, "SA", "SB", start_time, 2
    )

    # 1. Check Arrival Time (Sanity Check)
    assert arrival_times["SB"] == 435

    # 2. Check Path Structure and Length
    # Expected path: Start -> Trip segment (SA to SB)
    assert isinstance(path, list)
    assert len(path) == 2

    # 3. Check Start Step (Index 0)
    start_step = path[0]
    assert start_step["stop_id"] == "SA"
    assert start_step["arrival_time"] == start_time
    assert start_step["mode"] == "start"
    assert start_step["from_stop_id"] is None

    # 4. Check Trip Step (Index 1)
    trip_step = path[1]
    assert trip_step["stop_id"] == "SB"
    assert trip_step["from_stop_id"] == "SA"
    assert trip_step["arrival_time"] == 435
    assert trip_step["mode"] == "trip"
    assert trip_step["route_id"] == "R1"
    assert trip_step["trip_id"] == "T101"
    assert trip_step["transfer_time"] is None


def test_full_path_reconstruction_with_transfer():
    """
    Tests the path reconstruction for a two-trip journey connected by a transfer.
    Verifies that the path contains the correct sequence of Stop IDs, Trip IDs,
    and the Transfer segment.
    """
    # Create stops
    a = Stop("SA", 2, -33.918, 18.423, name="Stop A")
    b = Stop("SB", 2, -33.935, 18.413, name="Stop B")
    c = Stop("SC", 2, -34.05, 18.35, name="Stop C")
    d = Stop("SD", 2, -34.06, 18.36, name="Stop D")

    stops_dict = {s.id: s for s in [a, b, c, d]}

    # Route 1: SA -> SB
    route1 = Route("R1", [a, b], [])
    route1.add_trip(
        Trip("T101", [420, 430])
    )  # Departs A at 7:00 (420), Arrives B at 7:10 (430)

    # Route 2: SC -> SD
    route2 = Route("R2", [c, d], [])
    route2.add_trip(
        Trip("T201", [440, 450])
    )  # Departs C at 7:20 (440), Arrives D at 7:30 (450)

    routes = {route1.id: route1, route2.id: route2}

    # Transfer: SB -> SC (takes 5 minutes)
    transfers = [Transfer(b, c, 5)]

    # Start just before the first trip's departure
    start_time = 415

    # check for duplicate stops in route
    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from SA to SD
    arrival_times, path = raptor_algo(
        stops_dict, routes, transfers, "SA", "SD", start_time, 3
    )

    # 1. Check Arrival Times (Sanity Check)
    assert arrival_times["SD"] == 450
    assert arrival_times["SC"] == 435  # Arrive at C via transfer at 430 + 5 = 435

    # 2. Check Path Structure and Length
    # Expected path: Start -> R1/T101 (SA to SB) -> Transfer (SB to SC) -> R2/T201 (SC to SD)
    assert isinstance(path, list)
    assert len(path) == 4

    # 3. Check Start Step (Index 0)
    start_step = path[0]
    assert start_step["stop_id"] == "SA"
    assert start_step["mode"] == "start"
    assert start_step["arrival_time"] == start_time
    assert start_step["from_stop_id"] is None

    # 4. Check First Trip Segment (Index 1)
    trip1_step = path[1]
    assert trip1_step["stop_id"] == "SB"
    assert trip1_step["from_stop_id"] == "SA"
    assert trip1_step["arrival_time"] == 430
    assert trip1_step["mode"] == "trip"
    assert trip1_step["route_id"] == "R1"
    assert trip1_step["trip_id"] == "T101"

    # 5. Check Transfer Segment (Index 2)
    transfer_step = path[2]
    assert transfer_step["stop_id"] == "SC"
    assert transfer_step["from_stop_id"] == "SB"
    assert transfer_step["arrival_time"] == 435  # 430 + 5
    assert transfer_step["mode"] == "transfer"
    assert transfer_step["transfer_time"] == 5
    assert transfer_step["trip_id"] is None

    # 6. Check Second Trip Segment (Index 3 - Final Destination)
    trip2_step = path[3]
    assert trip2_step["stop_id"] == "SD"
    assert trip2_step["from_stop_id"] == "SC"
    assert trip2_step["arrival_time"] == 450
    assert trip2_step["mode"] == "trip"
    assert trip2_step["route_id"] == "R2"
    assert trip2_step["trip_id"] == "T201"


def test_path_object_creation_with_transfer_object():
    """
    Tests that the path includes the actual Transfer object for transfer segments.
    """
    # 1. Setup Data
    a = Stop("SA", 2, -33.918, 18.423, name="Stop A")
    b = Stop("SB", 2, -33.935, 18.413, name="Stop B")
    c = Stop("SC", 2, -34.05, 18.35, name="Stop C")
    d = Stop("SD", 2, -34.06, 18.36, name="Stop D")

    stops_dict = {s.id: s for s in [a, b, c, d]}

    route1 = Route("R1", [a, b], [])
    trip1 = Trip("T101", [420, 430])
    route1.add_trip(trip1)

    route2 = Route("R2", [c, d], [])
    trip2 = Trip("T201", [440, 450])
    route2.add_trip(trip2)

    routes_dict = {route1.id: route1, route2.id: route2}

    # Define the specific transfer object
    transfer_b_c = Transfer(b, c, 5)
    transfers = [transfer_b_c]

    # Preprocessing: Create the necessary lookup map
    transfers_map = hf.create_transfer_map(
        transfers
    )  # Key: ('SB', 'SC') -> transfer_b_c

    start_time = 415

    # check for duplicate stops in route
    for route in routes_dict.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # 2. Run RAPTOR
    _, path_ids = raptor_algo(
        stops_dict, routes_dict, transfers, "SA", "SD", start_time, 3
    )

    # 3. Reconstruct Path with Objects
    # Pass the new transfers_map argument
    path_objs = reconstruct_path_objs(path_ids, stops_dict, routes_dict, transfers_map)

    # 4. Assertions on Hydrated Path

    # Step 2: First Trip Segment (Sanity Check)
    trip1_step = path_objs[1]
    assert trip1_step["mode"] == "trip"
    assert "transfer_object" not in trip1_step
    assert trip1_step["trip_object"] is trip1

    # Step 3: Transfer Segment (SB -> SC)
    transfer_step = path_objs[2]
    assert transfer_step["mode"] == "transfer"
    assert transfer_step["from_stop_object"] is b
    assert transfer_step["stop_object"] is c

    # **KEY ASSERTION: Check the Transfer Object**
    assert "transfer_object" in transfer_step
    assert transfer_step["transfer_object"] is transfer_b_c
    assert transfer_step["transfer_object"].walking_time == 5

    # Step 4: Second Trip Segment (Sanity Check)
    trip2_step = path_objs[3]
    assert trip2_step["mode"] == "trip"
    assert trip2_step["trip_object"] is trip2
    assert "transfer_object" not in trip2_step


def test_gtfs_reader():
    # load GTFS data
    gtfs = GTFSReader()
    stops = gtfs.stops
    routes = gtfs.routes
    trips = gtfs.trips

    transfers = hf.create_transfers(stops, 200)  # just to test it runs

    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)


def test_simple_gtfs_raptor():
    # load GTFS data
    gtfs = GTFSReader()
    stops = gtfs.stops
    routes = gtfs.routes
    trips = gtfs.trips

    stop_ids = list(stops.keys())
    assert len(stop_ids) >= 2, "Not enough stops in GTFS data."

    # For testing, pick two stops on a single route
    source_stop_id = "mr_15"
    target_stop_id = "mr_135"

    # "mr_1" is never used in routes, so it should be unreachable
    unreachable_stop_id = "mr_1"  # other than walking
    # TODO: add test for unreachable stop - should be able to reach other stops by walking to a
    # different stop and then taking a route

    # create transfers
    transfers = raptor.helper_functions.create_transfers(stops, max_walking_dist=10000)
    print(transfers)

    for route in routes.values():
        check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from source to target, starting at 8:00 AM (480 minutes)
    arrival_times, path = raptor_algo(
        stops, routes, transfers, source_stop_id, target_stop_id, 480, 5
    )
    assert arrival_times[source_stop_id] == 480
    assert path != [], "Path should not be empty."
    assert arrival_times[target_stop_id] >= 480
    print()
