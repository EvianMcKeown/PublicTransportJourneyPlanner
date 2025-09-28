import csv
from pathlib import Path
from algorithm_prototype import raptor
from algorithm_prototype.raptor import (
    Stop,
    Route,
    Trip,
    Transfer,
    INF,
    MIN_TRANSFER_TIME,
    helper_functions as hf,
    raptor_algo,
    reconstruct_path,
    reconstruct_path_objs,
    check_duplicate_stops,
    check_transfer_loops,
    check_self_loops,
    check_predecessor_cycles,
)
from algorithm_prototype.gtfs_reader import GTFSReader
from datetime import timedelta
import pytest


"""
-------------------------------------------------------------
    UNIT TESTS FOR RAPTOR ALGORITHM
-------------------------------------------------------------
"""


def test_haversine_and_walkable_basic():
    # ~111 km per degree lat; 0.001 deg ~ 111 m
    a = Stop("A", 0, -33.0, 18.0)
    b = Stop("B", 0, -33.001, 18.0)
    d_m = hf.haversine(a.lat, a.lon, b.lat, b.lon)
    assert 100 <= d_m <= 120  # rough band

    # Walkable threshold 150 m => should be walkable
    assert hf.walkable(a.lat, a.lon, b.lat, b.lon, dist=150) is True
    # Threshold 50 m => not walkable
    assert hf.walkable(a.lat, a.lon, b.lat, b.lon, dist=50) is False


def test_estimate_via_times_and_check_times():
    # VIA between 08:00 and 08:10 -> expect ~08:05
    times = [480, INF, 490]
    is_via = [False, True, False]
    est = hf._estimate_via_times(times, is_via)
    assert est[1] == 485

    ok, idx = hf._check_trip_times([480, 485, 490, 490, 492])
    assert ok is True and idx == -1

    # negative edge should fail
    ok, idx = hf._check_trip_times([480, 470, 490])
    assert ok is False and idx == 1


def test_create_transfers_and_map_min_time():
    # Two nearby stops and one far stop
    s1 = Stop("S1", 1, -33.0, 18.0)
    s2 = Stop("S2", 1, -33.0005, 18.0)  # close
    s3 = Stop("S3", 1, -34.0, 18.0)  # far

    transfers = hf.create_transfers(
        {"S1": s1, "S2": s2, "S3": s3}, max_walking_dist=200
    )
    # Should include S1->S2 and S2->S1, but not S3
    ids = {(t.from_stop.id, t.to_stop.id) for t in transfers}
    assert ("S1", "S2") in ids and ("S2", "S1") in ids
    assert all("S3" not in pair for pair in ids)

    # Check transfer time uses MIN_TRANSFER_TIME as floor
    t_s1_s2 = next(
        t for t in transfers if t.from_stop.id == "S1" and t.to_stop.id == "S2"
    )
    assert t_s1_s2.walking_time >= MIN_TRANSFER_TIME

    # Map creation
    tmap = hf.create_transfer_map(transfers)
    assert ("S1", "S2") in tmap and tmap[("S1", "S2")].to_stop.id == "S2"


def test_safe_set_predecessor_detects_2cycle_in_debug():
    # Build a small predecessor layer and force a 2-cycle
    predecessor = [None] * 5
    idx_to_id = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E"}

    # Set A <- B first
    assert (
        hf.safe_set_predecessor(
            current_idx=0,
            prev_idx=1,
            arrival_time=100,
            mode="transfer",
            route_id=None,
            trip_id=None,
            transfer_time=5,
            predecessor=predecessor,
            idx_to_id=idx_to_id,
            debug=False,
        )
        is True
    )

    # Now try B <- A with debug=True -> should raise (2-cycle)
    with pytest.raises(ValueError):
        hf.safe_set_predecessor(
            current_idx=1,
            prev_idx=0,
            arrival_time=105,
            mode="transfer",
            route_id=None,
            trip_id=None,
            transfer_time=5,
            predecessor=predecessor,
            idx_to_id=idx_to_id,
            debug=True,
        )


def test_reconstruct_path_cycle_detection_raises():
    # Simulate a small predecessor_layers with a deliberate cycle
    n = 3
    max_rounds = 3
    predecessor_layers = [[None] * n for _ in range(max_rounds + 1)]
    idx_to_id = {0: "S0", 1: "S1", 2: "S2"}

    # Round assignments
    improved_round = [-1, -1, -1]
    # Set target S2 improved in round 2
    improved_round[2] = 2

    # Round 2: S2 <- S1
    predecessor_layers[2][2] = {
        "prev_idx": 1,
        "arrival_time": 200,
        "mode": "transfer",
        "route_id": None,
        "trip_id": None,
        "transfer_time": 5,
        "prev_round": 2,
    }
    # Round 2: S1 <- S2 (forms 2-cycle in same round)
    predecessor_layers[2][1] = {
        "prev_idx": 2,
        "arrival_time": 195,
        "mode": "transfer",
        "route_id": None,
        "trip_id": None,
        "transfer_time": 5,
        "prev_round": 2,
    }

    with pytest.raises(ValueError):
        reconstruct_path(
            predecessor_layers=predecessor_layers,
            improved_round=improved_round,
            idx_to_id=idx_to_id,
            target_idx=2,
            source_idx=0,
            result={"S0": 100, "S1": 195, "S2": 200},
        )


def test_reconstruct_path_objs_uses_board_and_disembark_pos():
    # Build a simple route with two stops and one trip
    a = Stop("A", 2, -33.918, 18.423)
    b = Stop("B", 2, -33.935, 18.413)
    route = Route("R1", [a, b], [])
    trip = Trip("T1_day0", [480, 485])
    route.add_trip(trip)

    routes_dict = {route.id: route}
    stops_dict = {"A": a, "B": b}
    transfers_map = {}

    # Simulate a path returned by raptor_algo with board/disembark indices
    path = [
        {
            "stop_id": "A",
            "arrival_time": 480,
            "mode": "start",
            "from_stop_id": None,
            "route_id": None,
            "trip_id": None,
            "transfer_time": None,
        },
        {
            "stop_id": "B",
            "from_stop_id": "A",
            "arrival_time": 485,
            "mode": "trip",
            "route_id": "R1",
            "trip_id": "T1_day0",
            "transfer_time": None,
            "board_pos": 0,
            "disembark_pos": 1,
        },
    ]

    enriched = reconstruct_path_objs(
        path=path,
        stops_dict=stops_dict,
        routes_dict=routes_dict,
        transfers_dict=transfers_map,
    )

    trip_step = enriched[1]
    assert trip_step["route_object"] is route
    assert trip_step["trip_object"] is trip
    assert trip_step["board_stop_id"] == "A"
    assert trip_step["disembark_stop_id"] == "B"
    assert trip_step["board_stop_object"] is a
    assert trip_step["disembark_stop_object"] is b


def test_minimal_raptor_direct_trip_sets_board_and_disembark():
    # Direct trip A->B at 08:00->08:05
    a = Stop("A", 2, -33.918, 18.423)
    b = Stop("B", 2, -33.935, 18.413)
    route = Route("R1", [a, b], [])
    route.add_trip(Trip("T1_day0", [480, 485]))
    routes = {"R1": route}
    stops = {"A": a, "B": b}
    transfers = []

    result, path = raptor_algo(
        stops=stops,
        routes=routes,
        transfers=transfers,
        source_id="A",
        target_id="B",
        departure_time=480,
        max_rounds=3,
        debug=True,
    )

    assert result["B"] == 485
    assert len(path) == 2
    step = path[1]
    assert step["mode"] == "trip"
    # board/disembark positions should be present for reconstruct_path_objs to use
    assert step.get("board_pos") == 0
    assert step.get("disembark_pos") == 1


@pytest.fixture
def minimal_gtfs(tmp_path: Path) -> str:
    """
    Create a minimal GTFS set:
    - One route ga_1-0 (GABS)
    - Two stops: GABS001 (S1), GABS006 (S2)
    - One trip ga_29 with stop_times at 08:00 and 08:05
    - Calendar active on Monday (day 0)
    """
    gtfs_root = tmp_path / "gtfs"
    # stops.txt
    _write_csv(
        gtfs_root / "stops.txt",
        ["stop_id", "stop_name", "stop_lat", "stop_lon"],
        [
            ["GABS001", "Bellville", "-33.90587816", "18.62981745"],
            ["GABS006", "Elsies River", "-33.91175302", "18.56794156"],
        ],
    )
    # routes.txt
    _write_csv(
        gtfs_root / "routes.txt",
        ["route_id", "agency_id", "route_short_name"],
        [
            ["ga_1-0", "GABS", "1"],
        ],
    )
    # trips.txt
    _write_csv(
        gtfs_root / "trips.txt",
        [
            "route_id",
            "service_id",
            "trip_id",
            "trip_headsign",
            "direction_id",
            "block_id",
            "shape_id",
        ],
        [
            ["ga_1-0", "svc1", "ga_29", "Test", "0", "", ""],
        ],
    )
    # stop_times.txt (trip visits GABS001 then GABS006)
    _write_csv(
        gtfs_root / "stop_times.txt",
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        [
            ["ga_29", "08:00:00", "08:00:00", "GABS001", "1"],
            ["ga_29", "08:05:00", "08:05:00", "GABS006", "2"],
        ],
    )
    # calendar.txt (service active Monday)
    _write_csv(
        gtfs_root / "calendar.txt",
        [
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        [
            ["svc1", "1", "0", "0", "0", "0", "0", "0"],
        ],
    )
    # return folder path string with trailing slash (as reader concatenates)
    return str(gtfs_root) + "/"


def _write_csv(path: Path, header: list[str], rows: list[list[str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _write_path_objs_csv(out_path: Path, journey: list[dict]):
    """
    Write the reconstructed journey (object-referenced) to CSV.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "step_idx",
        "mode",
        "arrival_time_mins",
        "arrival_time_str",
        "from_stop_id",
        "stop_id",
        "route_id",
        "trip_id",
        "transfer_time",
        "board_pos",
        "disembark_pos",
        "board_stop_id",
        "disembark_stop_id",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i, step in enumerate(journey):
            t = step.get("arrival_time")
            t_str = GTFSReader.mins_to_str(t) if isinstance(t, int) else ""
            w.writerow(
                [
                    i,
                    step.get("mode"),
                    t,
                    t_str,
                    step.get("from_stop_id"),
                    step.get("stop_id"),
                    step.get("route_id"),
                    step.get("trip_id"),
                    step.get("transfer_time"),
                    step.get("board_pos"),
                    step.get("disembark_pos"),
                    step.get("board_stop_id"),
                    step.get("disembark_stop_id"),
                ]
            )


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

    #    for route in routes.values():
    #        check_duplicate_stops(route)
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
    source_stop_id = "mr_135"
    target_stop_id = "mc_BIG_BAY"

    # "mr_1" is never used in routes, so it should be unreachable
    unreachable_stop_id = "mr_1"  # other than walking
    # TODO: add test for unreachable stop - should be able to reach other stops by walking to a
    # different stop and then taking a route

    # create transfers
    transfers = raptor.helper_functions.create_transfers(stops, max_walking_dist=10000)
    # print(transfers)

    # for route in routes.values():
    #    check_duplicate_stops(route)
    check_transfer_loops(transfers)

    # Run RAPTOR from source to target, starting at 8:00 AM (480 minutes)
    arrival_times, path = raptor_algo(
        stops, routes, transfers, source_stop_id, target_stop_id, 480, 5
    )
    origin_time = arrival_times[source_stop_id]
    assert origin_time == 480
    assert path != [], "Path should not be empty."
    target_time = arrival_times[target_stop_id]
    assert target_time >= 480
    assert target_time == path[len(path) - 1]["arrival_time"]
    assert GTFSReader.mins_to_str(origin_time) == "Mon 08:00"
    assert GTFSReader.mins_to_str(target_time) == "Mon 09:23"
    # print()


def test_gtfs_reader_raptor_reconstruct_objs(minimal_gtfs: str, tmp_path: Path):
    # 1) Load GTFS
    reader = GTFSReader(gtfs_folder=minimal_gtfs)

    # sanity checks
    assert "GABS001" in reader.stops and "GABS006" in reader.stops
    assert "ga_1-0" in reader.routes
    route = reader.routes["ga_1-0"]
    # canonical sequence should match trip (2 occurrences)
    assert [s.id for s in route.stops] == ["GABS001", "GABS006"]
    # at least one expanded trip (svc1 on Monday -> _day0)
    assert any(t.id.startswith("ga_29_day0") for t in route.trips)

    # 2) Build transfers map (empty is fine; no walking needed)
    transfers = []  # no transfers needed for this simple test
    transfer_map = raptor.helper_functions.create_transfer_map(transfers)

    # 3) Run RAPTOR from GABS001 at 08:00 to GABS006
    dep_time = 8 * 60  # 480
    result, path = raptor_algo(
        stops=reader.stops,
        routes=reader.routes,
        transfers=transfers,
        source_id="GABS001",
        target_id="GABS006",
        departure_time=dep_time,
        max_rounds=5,
        debug=True,
    )

    # earliest arrival is 08:05
    assert result["GABS006"] == 8 * 60 + 5

    # path should be: start -> one trip step
    assert len(path) >= 2
    assert path[0]["mode"] == "start"
    trip_step = next((s for s in path if s.get("mode") == "trip"), None)
    assert trip_step is not None, f"Expected a trip step, got {path}"

    # Validate trip step fields and boarding/disembark positions are present
    assert trip_step["route_id"] == "ga_1-0"
    assert trip_step["trip_id"].startswith("ga_29_day0")
    assert trip_step.get("board_pos") == 0
    assert trip_step.get("disembark_pos") == 1
    assert trip_step["from_stop_id"] == "GABS001"
    assert trip_step["stop_id"] == "GABS006"

    # 4) Reconstruct objects using board_pos/disembark_pos
    path_objs = reconstruct_path_objs(
        path=path,
        stops_dict=reader.stops,
        routes_dict=reader.routes,
        transfers_dict=transfer_map,
    )

    # 5) Write to test result CSV
    output_folder = str(Path(__file__).parent) + "/test_output/"
    out_csv = Path(output_folder) / "minimal_gtfs_path.csv"
    _write_path_objs_csv(out_csv, path_objs)

    # 6) Assertions on reconstructed objects
    trip_obj_step = next((s for s in path_objs if s.get("mode") == "trip"), None)
    assert trip_obj_step is not None
    assert "route_object" in trip_obj_step and isinstance(
        trip_obj_step["route_object"], Route
    )
    assert "trip_object" in trip_obj_step and isinstance(
        trip_obj_step["trip_object"], Trip
    )
    assert trip_obj_step.get("board_stop_object") is not None
    assert trip_obj_step.get("disembark_stop_object") is not None
    assert trip_obj_step["board_stop_id"] == "GABS001"
    assert trip_obj_step["disembark_stop_id"] == "GABS006"


def test_gtfs_midnight_wrap_raptor_reconstruct_objs(tmp_path: Path):
    """
    Build a tiny GTFS feed where a trip departs at 23:55 (Mon) and arrives 00:05 (Tue).
    Verify RAPTOR finds it and formatting wraps to Tue 00:05.
    """
    gtfs_root = tmp_path / "gtfs_midnight"
    # stops.txt
    _write_csv(
        gtfs_root / "stops.txt",
        ["stop_id", "stop_name", "stop_lat", "stop_lon"],
        [
            ["GABS001", "Bellville", "-33.90587816", "18.62981745"],
            ["GABS006", "Elsies River", "-33.91175302", "18.56794156"],
        ],
    )
    # routes.txt
    _write_csv(
        gtfs_root / "routes.txt",
        ["route_id", "agency_id", "route_short_name"],
        [
            ["ga_1-0", "GABS", "1"],
        ],
    )
    # trips.txt
    _write_csv(
        gtfs_root / "trips.txt",
        [
            "route_id",
            "service_id",
            "trip_id",
            "trip_headsign",
            "direction_id",
            "block_id",
            "shape_id",
        ],
        [
            ["ga_1-0", "svc1", "ga_99", "LateNight", "0", "", ""],
        ],
    )
    # stop_times.txt (23:55 -> 24:05)
    _write_csv(
        gtfs_root / "stop_times.txt",
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        [
            ["ga_99", "23:55:00", "23:55:00", "GABS001", "1"],
            ["ga_99", "24:05:00", "24:05:00", "GABS006", "2"],
        ],
    )
    # calendar.txt (service active Monday only)
    _write_csv(
        gtfs_root / "calendar.txt",
        [
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        [
            ["svc1", "1", "0", "0", "0", "0", "0", "0"],
        ],
    )

    reader = GTFSReader(gtfs_folder=str(gtfs_root) + "/")
    assert "ga_1-0" in reader.routes
    route = reader.routes["ga_1-0"]
    assert [s.id for s in route.stops] == ["GABS001", "GABS006"]

    # Run RAPTOR from 23:50 (Mon) so we can catch the 23:55 departure
    dep_time = 23 * 60 + 50  # 1430
    result, path = raptor_algo(
        stops=reader.stops,
        routes=reader.routes,
        transfers=[],
        source_id="GABS001",
        target_id="GABS006",
        departure_time=dep_time,
        max_rounds=4,
        debug=True,
    )

    # Expected arrival is 24:05 => Tue 00:05 (minutes = 1445)
    assert result["GABS006"] == 24 * 60 + 5
    assert GTFSReader.mins_to_str(result["GABS006"]) == "Tue 00:05"

    # Verify the trip step exists and indices are present
    trip_step = next(s for s in path if s.get("mode") == "trip")
    assert trip_step["route_id"] == "ga_1-0"
    assert trip_step["trip_id"].startswith("ga_99_day0")
    assert trip_step.get("board_pos") == 0
    assert trip_step.get("disembark_pos") == 1

    # Reconstruct objects using indices
    path_objs = reconstruct_path_objs(
        path=path,
        stops_dict=reader.stops,
        routes_dict=reader.routes,
        transfers_dict=hf.create_transfer_map([]),
    )
    trip_obj_step = next(s for s in path_objs if s.get("mode") == "trip")
    assert trip_obj_step["board_stop_id"] == "GABS001"
    assert trip_obj_step["disembark_stop_id"] == "GABS006"


def test_week_wrap_formatting_and_raptor(tmp_path: Path):
    """
    Build a feed with a Sunday night trip 23:58 -> 24:02 (Monday 00:02 next day).
    Verify arrival formatting wraps to Mon 00:02 and absolute minutes exceed one week if needed.
    """
    gtfs_root = tmp_path / "gtfs_weekwrap"
    # stops.txt
    _write_csv(
        gtfs_root / "stops.txt",
        ["stop_id", "stop_name", "stop_lat", "stop_lon"],
        [
            ["S1", "Stop 1", "-33.90", "18.62"],
            ["S2", "Stop 2", "-33.91", "18.57"],
        ],
    )
    # routes.txt
    _write_csv(
        gtfs_root / "routes.txt",
        ["route_id", "agency_id", "route_short_name"],
        [
            ["rw_1-0", "GABS", "W1"],
        ],
    )
    # trips.txt
    _write_csv(
        gtfs_root / "trips.txt",
        [
            "route_id",
            "service_id",
            "trip_id",
            "trip_headsign",
            "direction_id",
            "block_id",
            "shape_id",
        ],
        [
            ["rw_1-0", "svc7", "rw_701", "SunLate", "0", "", ""],
        ],
    )
    # stop_times.txt (23:58 -> 24:02)
    _write_csv(
        gtfs_root / "stop_times.txt",
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        [
            ["rw_701", "23:58:00", "23:58:00", "S1", "1"],
            ["rw_701", "24:02:00", "24:02:00", "S2", "2"],
        ],
    )
    # calendar.txt (service active Sunday only)
    _write_csv(
        gtfs_root / "calendar.txt",
        [
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        [
            ["svc7", "0", "0", "0", "0", "0", "0", "1"],
        ],
    )

    reader = GTFSReader(gtfs_folder=str(gtfs_root) + "/")
    assert "rw_1-0" in reader.routes
    route = reader.routes["rw_1-0"]
    assert [s.id for s in route.stops] == ["S1", "S2"]

    # Sunday offset is day 6 -> 6*1440; depart 23:58 => 6*1440 + 1438
    dep_time = 6 * 24 * 60 + (23 * 60 + 58)
    result, path = raptor_algo(
        stops=reader.stops,
        routes=reader.routes,
        transfers=[],
        source_id="S1",
        target_id="S2",
        departure_time=dep_time,
        max_rounds=3,
        debug=True,
    )

    # Expected arrival is 6*1440 + 1442 absolute minutes (wraps to Mon 00:02 in display)
    expected_arrival = 6 * 24 * 60 + (24 * 60 + 2)
    assert result["S2"] == expected_arrival
    assert GTFSReader.mins_to_str(result["S2"]) == "Mon 00:02"

    # Ensure trip step present with indices
    trip_step = next(s for s in path if s.get("mode") == "trip")
    assert trip_step["route_id"] == "rw_1-0"
    assert trip_step["trip_id"].startswith("rw_701_day6")
    assert trip_step.get("board_pos") == 0
    assert trip_step.get("disembark_pos") == 1

    # verify formatting wraps over a whole week (7 days) correctly
    seven_days_plus = 7 * 24 * 60 + 62  # Mon + 01:02 next week
    assert GTFSReader.mins_to_str(seven_days_plus) == "Mon 01:02"
