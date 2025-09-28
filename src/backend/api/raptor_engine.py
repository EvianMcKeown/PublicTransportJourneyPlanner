from __future__ import annotations

import threading
from typing import Any, List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from django.conf import settings

from algorithm_prototype.gtfs_reader import GTFSReader, INF
from algorithm_prototype.raptor import (
    helper_functions as hf,
    raptor_algo,
    reconstruct_path_objs,
    Stop,
    Route,
    Trip,
    Transfer,
    MAX_WALK_DIST,
)


def to_mins(day: Optional[int], time_str: str) -> int:
    """
    Convert an optional day (0=Mon..6=Sun) and a time string "HH:MM" or "HH:MM:SS"
    into absolute minutes since Monday 00:00. If day is None, returns minutes
    since midnight (0..1439).

    Raises ValueError on invalid input.
    """
    if not isinstance(time_str, str):
        raise ValueError("time_str must be a string like 'HH:MM' or 'HH:MM:SS'.")

    parts = time_str.strip().split(":")
    if len(parts) < 2:
        raise ValueError("time_str must be in 'HH:MM' or 'HH:MM:SS' format.")

    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except ValueError as e:
        raise ValueError("time_str contains non-integer components.") from e

    if not (0 <= mm < 60):
        raise ValueError("Minutes must be in the range 0..59.")

    # seconds are optional; ignored if present
    total = hh * 60 + mm

    if day is None:
        return total

    if not isinstance(day, int) or not (0 <= day <= 6):
        raise ValueError("day must be an integer in the range 0..6 (Mon..Sun).")

    return day * 24 * 60 + total


def _serialize_stop(s: Stop) -> Dict[str, Any]:
    return {
        "id": s.id,
        "name": getattr(s, "name", ""),
        "lat": s.lat,
        "lon": s.lon,
        "mode": s.mode,
    }


def _serialize_route(r: Route) -> Dict[str, Any]:
    return {"id": r.id, "name": getattr(r, "name", ""), "mode": r.mode}


def _serialize_trip(t: Trip) -> Dict[str, Any]:
    return {"id": t.id}


def _path_objs_to_json_safe(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for step in steps:
        s = {
            # common
            "mode": step.get("mode"),
            "arrival_time": step.get("arrival_time"),
            "stop_id": step.get("stop_id"),
            "from_stop_id": step.get("from_stop_id"),
            "route_id": step.get("route_id"),
            "trip_id": step.get("trip_id"),
            "transfer_time": step.get("transfer_time"),
            # indices (to help UI debugging)
            "board_pos": step.get("board_pos"),
            "disembark_pos": step.get("disembark_pos"),
        }
        # include objects when available
        if "stop_object" in step and step["stop_object"]:
            s["stop"] = _serialize_stop(step["stop_object"])
        if "from_stop_object" in step and step["from_stop_object"]:
            s["from_stop"] = _serialize_stop(step["from_stop_object"])
        if "route_object" in step and step["route_object"]:
            s["route"] = _serialize_route(step["route_object"])
        if "trip_object" in step and step["trip_object"]:
            s["trip"] = _serialize_trip(step["trip_object"])
        if "board_stop_object" in step and step["board_stop_object"]:
            s["board_stop"] = _serialize_stop(step["board_stop_object"])
        if "disembark_stop_object" in step and step["disembark_stop_object"]:
            s["disembark_stop"] = _serialize_stop(step["disembark_stop_object"])
        out.append(s)
    return out


class RaptorEngine:
    def __init__(self, gtfs_folder: Optional[str] = None):
        self._lock = threading.RLock()
        self._loaded = False
        self._gtfs_folder = gtfs_folder or getattr(settings, "GTFS_FOLDER", None)
        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.transfers: List[Transfer] = []
        self.transfer_map: Dict[Tuple[str, str], Transfer] = {}
        self.last_max_walk_distance: int = MAX_WALK_DIST

    def load(self, custom_max_walk_dist: Optional[int] = None) -> None:
        with self._lock:
            if self._loaded:
                return
            reader = GTFSReader(gtfs_folder=self._gtfs_folder)
            self.stops = reader.stops
            self.routes = reader.routes
            # build walk transfers (if non-default max_walk_distance is used, transfers need to be
            # created in the planner call)
            if custom_max_walk_dist is not None:
                self.last_max_walk_distance = custom_max_walk_dist
            else:
                self.last_max_walk_distance = MAX_WALK_DIST
            self.transfers = hf.create_transfers(
                self.stops, self.last_max_walk_distance
            )
            self.transfer_map = hf.create_transfer_map(self.transfers)
            self._loaded = True

    def plan(
        self,
        source_id: str,
        target_id: str,
        departure_minutes: int,
        max_rounds: int = 5,
        custom_max_walk_dist: Optional[int] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        if not self._loaded:
            self.load(custom_max_walk_dist=custom_max_walk_dist)
        else:
            # if max_walk_distance changed, rebuild transfers
            if (custom_max_walk_dist is not None) and (
                custom_max_walk_dist != self.last_max_walk_distance
            ):
                self.transfers = hf.create_transfers(
                    self.stops, custom_max_walk_dist or MAX_WALK_DIST
                )
                self.transfer_map = hf.create_transfer_map(self.transfers)
                self.last_max_walk_distance = custom_max_walk_dist or MAX_WALK_DIST

        # Run the algorithm
        result, path = raptor_algo(
            stops=self.stops,
            routes=self.routes,
            transfers=self.transfers,
            source_id=source_id,
            target_id=target_id,
            departure_time=departure_minutes,
            max_rounds=max_rounds,
            debug=debug,
        )
        # Enrich with objects (board_pos/disembark_pos aware), then make JSON-safe
        path_objs = reconstruct_path_objs(
            path=path,
            stops_dict=self.stops,
            routes_dict=self.routes,
            transfers_dict=self.transfer_map,
        )
        return {
            "result": result,
            "path": path,
            "path_objs": _path_objs_to_json_safe(path_objs),
        }


# Singleton with lazy load (pre-warmed in AppConfig.ready)
_engine: Optional[RaptorEngine] = None
_engine_lock = threading.RLock()
# The two-phase logic separates object construction from data loading.
# Construction happens when _engine is None; loading is guarded by
# the _engine._loaded flag so expensive GTFS reading and transfer building
# occur once. Using threading.RLock makes the accessor safe under concurrent access.


def get_engine() -> RaptorEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = RaptorEngine(getattr(settings, "GTFS_FOLDER", None))
        if not _engine._loaded:
            _engine.load()
        return _engine
