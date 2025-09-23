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
    result = raptor_algo(stops_dict, routes, transfers, "A", "C", 410, 5)
    assert result["A"] == 410
    assert result["B"] == 430
    assert result["C"] == 450


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
    result = raptor_algo(stops_dict, routes, transfers, "A", "D", 420, 5)

    # Expected: A=420, B=430, C=435 (B->C transfer), D=450 (on trip T2)
    assert result["A"] == 420
    assert result["B"] == 430
    assert result["C"] == 435
    assert result["D"] == 450


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
    result = raptor_algo(stops_dict, routes, transfers, "A", "D", 420, 5)

    # Expected: A=420, B=430, C=435 (B->C transfer), D=445 (on trip T2)
    assert result["A"] == 420
    assert result["B"] == 430
    assert result["C"] == 435
    assert result["D"] == 445


def test_gtfs_route_with_transfer():
    # load GTFS data
    gtfs = GTFSReader()
    stops = gtfs.stops
    routes = gtfs.routes
    trips = gtfs.trips

    # Pick two stops on different routes that are within walking distance
    stop_ids = list(stops.keys())
    assert len(stop_ids) >= 2, "Not enough stops in GTFS data."
