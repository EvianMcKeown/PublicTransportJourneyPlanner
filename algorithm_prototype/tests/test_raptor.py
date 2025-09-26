from algorithm_prototype import raptor
from algorithm_prototype.raptor import Stop, Route, Trip, Transfer, raptor_algo
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

    # Run RAPTOR from A to E, starting at 7:00 (420)
    arrival_times, path = raptor_algo(stops_dict, routes, transfers, "A", "E", 420, 5)

    # Expected fastest path: A(420) -> B(430) -> Transfer -> E(435)
    # The alternative path A(420) -> D(435) -> E(440) is slower.
    assert arrival_times["A"] == 420
    assert arrival_times["B"] == 430
    assert arrival_times["E"] == 435
    # assert path["E"][0].stop_id == "B" # Path must arrive from B


def test_gtfs_reader():
    # load GTFS data
    gtfs = GTFSReader()
    stops = gtfs.stops
    routes = gtfs.routes
    trips = gtfs.trips

    # Pick two stops on different routes that are within walking distance
    stop_ids = list(stops.keys())
    assert len(stop_ids) >= 2, "Not enough stops in GTFS data."


def test_simple_gtfs_raptor():
    # load GTFS data
    gtfs = GTFSReader()
    stops = gtfs.stops
    routes = gtfs.routes
    trips = gtfs.trips

    stop_ids = list(stops.keys())
    assert len(stop_ids) >= 2, "Not enough stops in GTFS data."

    # For testing, pick two stops on routes
    source_stop_id = "mr_2"
    target_stop_id = "mr_72"

    # "mr_1" is never used in routes, so it should be unreachable
    unreachable_stop_id = "mr_1"  # other than walking
    # TODO: add test for unreachable stop - should be able to reach other stops by walking to a
    # different stop and then taking a route

    # create transfers
    transfers = raptor.helper_functions.create_transfers(stops)

    # Run RAPTOR from source to target, starting at 8:00 AM (480 minutes)
    arrival_times, path = raptor_algo(
        stops, routes, transfers, source_stop_id, target_stop_id, 480, 5
    )
    assert arrival_times[source_stop_id] == 480
    print()
    assert arrival_times[target_stop_id] >= 480
    print()
