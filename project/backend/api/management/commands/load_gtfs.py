import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from api.models import (
    Agency,
    Calendar,
    CalendarDate,
    Route,
    Stop,
    Trip,
    StopTime,
)


def bool_from_1(value):
    return str(value).strip() == "1"


class Command(BaseCommand):
    help = "Load GTFS text files (agency, calendar, calendar_dates, routes, stops, trips, stop_times) into the DB"

    def add_arguments(self, parser):
        parser.add_argument("gtfs_path", type=str, help="Path to folder containing GTFS .txt files")

    def handle(self, *args, **options):
        path = options["gtfs_path"]
        if not os.path.isdir(path):
            self.stderr.write(self.style.ERROR(f"Path not found: {path}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Loading GTFS files from: {path}"))

        # Use transactions per-file so partial failures don't corrupt other files
        # 1) agency.txt
        agency_file = os.path.join(path, "agency.txt")
        if os.path.exists(agency_file):
            with transaction.atomic():
                count = 0
                with open(agency_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        agency_id = row.get("agency_id") or (row.get("agency_name") or "").strip()[:50] or f"agency_{count}"
                        Agency.objects.update_or_create(
                            agency_id=agency_id,
                            defaults={
                                "name": row.get("agency_name", "").strip(),
                                "url": row.get("agency_url", "").strip(),
                                "timezone": row.get("agency_timezone", "").strip(),
                                "lang": row.get("agency_lang", "").strip() or None,
                                "phone": row.get("agency_phone", "").strip() or None,
                            },
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} agencies"))
        else:
            self.stdout.write(self.style.WARNING("agency.txt not found — skipping"))

        # 2) calendar.txt
        calendar_file = os.path.join(path, "calendar.txt")
        if os.path.exists(calendar_file):
            with transaction.atomic():
                count = 0
                with open(calendar_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        service_id = row.get("service_id")
                        if not service_id:
                            self.stdout.write(self.style.WARNING("Skipping calendar row without service_id"))
                            continue
                        try:
                            start = parse_date(row.get("start_date")) if row.get("start_date") else None
                            end = parse_date(row.get("end_date")) if row.get("end_date") else None
                        except Exception:
                            start = end = None
                        Calendar.objects.update_or_create(
                            service_id=service_id,
                            defaults={
                                "monday": bool_from_1(row.get("monday", "")),
                                "tuesday": bool_from_1(row.get("tuesday", "")),
                                "wednesday": bool_from_1(row.get("wednesday", "")),
                                "thursday": bool_from_1(row.get("thursday", "")),
                                "friday": bool_from_1(row.get("friday", "")),
                                "saturday": bool_from_1(row.get("saturday", "")),
                                "sunday": bool_from_1(row.get("sunday", "")),
                                "start_date": start,
                                "end_date": end,
                            },
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} calendar entries"))
        else:
            self.stdout.write(self.style.WARNING("calendar.txt not found — skipping"))

        # 3) calendar_dates.txt
        caldates_file = os.path.join(path, "calendar_dates.txt")
        if os.path.exists(caldates_file):
            with transaction.atomic():
                count = 0
                with open(caldates_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        service_id = row.get("service_id")
                        date_str = row.get("date")
                        exc_type = row.get("exception_type")
                        if not service_id or not date_str:
                            self.stdout.write(self.style.WARNING("Skipping calendar_date row missing service_id or date"))
                            continue
                        service = Calendar.objects.filter(service_id=service_id).first()
                        if not service:
                            self.stdout.write(self.style.WARNING(f"Calendar not found for service_id={service_id} — skipping calendar_date {date_str}"))
                            continue
                        try:
                            date_obj = parse_date(date_str)
                        except Exception:
                            self.stdout.write(self.style.WARNING(f"Bad date '{date_str}' — skipping"))
                            continue
                        CalendarDate.objects.update_or_create(
                            service=service,
                            date=date_obj,
                            defaults={"exception_type": int(exc_type) if exc_type and exc_type.isdigit() else 1},
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} calendar_dates entries"))
        else:
            self.stdout.write(self.style.WARNING("calendar_dates.txt not found — skipping"))

        # 4) routes.txt
        routes_file = os.path.join(path, "routes.txt")
        if os.path.exists(routes_file):
            with transaction.atomic():
                count = 0
                with open(routes_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        r_id = row.get("route_id")
                        if not r_id:
                            self.stdout.write(self.style.WARNING("Skipping route row without route_id"))
                            continue
                        agency_obj = None
                        agency_id = row.get("agency_id")
                        if agency_id:
                            agency_obj = Agency.objects.filter(agency_id=agency_id).first()
                        Route.objects.update_or_create(
                            route_id=r_id,
                            defaults={
                                "agency": agency_obj,
                                "short_name": row.get("route_short_name", "").strip(),
                                "long_name": row.get("route_long_name", "").strip(),
                            },
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} routes"))
        else:
            self.stdout.write(self.style.WARNING("routes.txt not found — skipping"))

        # 5) stops.txt
        stops_file = os.path.join(path, "stops.txt")
        if os.path.exists(stops_file):
            with transaction.atomic():
                count = 0
                with open(stops_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        s_id = row.get("stop_id")
                        if not s_id:
                            self.stdout.write(self.style.WARNING("Skipping stop row without stop_id"))
                            continue
                        try:
                            lat = float(row.get("stop_lat") or row.get("lat") or 0)
                            lon = float(row.get("stop_lon") or row.get("lon") or 0)
                        except Exception:
                            lat = lon = 0.0
                        Stop.objects.update_or_create(
                            stop_id=s_id,
                            defaults={
                                "name": row.get("stop_name", "").strip(),
                                "lat": lat,
                                "lon": lon,
                            },
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} stops"))
        else:
            self.stdout.write(self.style.WARNING("stops.txt not found — skipping"))

        # 6) trips.txt
        trips_file = os.path.join(path, "trips.txt")
        if os.path.exists(trips_file):
            with transaction.atomic():
                count = 0
                with open(trips_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        t_id = row.get("trip_id")
                        if not t_id:
                            self.stdout.write(self.style.WARNING("Skipping trip row without trip_id"))
                            continue
                        route_obj = Route.objects.filter(route_id=row.get("route_id")).first()
                        service_obj = Calendar.objects.filter(service_id=row.get("service_id")).first()
                        Trip.objects.update_or_create(
                            trip_id=t_id,
                            defaults={
                                "route": route_obj,
                                "service": service_obj,
                                "headsign": row.get("trip_headsign", "").strip(),
                                "direction_id": int(row.get("direction_id")) if row.get("direction_id") and row.get("direction_id").isdigit() else None,
                            },
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} trips"))
        else:
            self.stdout.write(self.style.WARNING("trips.txt not found — skipping"))

        # 7) stop_times.txt
        stoptimes_file = os.path.join(path, "stop_times.txt")
        if os.path.exists(stoptimes_file):
            with transaction.atomic():
                count = 0
                with open(stoptimes_file, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        trip_obj = Trip.objects.filter(trip_id=row.get("trip_id")).first()
                        stop_obj = Stop.objects.filter(stop_id=row.get("stop_id")).first()
                        if not trip_obj or not stop_obj:
                            self.stdout.write(self.style.WARNING(f"Skipping stop_time with missing trip or stop: trip={row.get('trip_id')}, stop={row.get('stop_id')}"))
                            continue
                        try:
                            seq = int(row.get("stop_sequence") or 0)
                        except Exception:
                            seq = 0
                        StopTime.objects.update_or_create(
                            trip=trip_obj,
                            stop_sequence=seq,
                            defaults={
                                "stop": stop_obj,
                                "arrival_time": row.get("arrival_time", "").strip(),
                                "departure_time": row.get("departure_time", "").strip(),
                            },
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded {count} stop_times"))
        else:
            self.stdout.write(self.style.WARNING("stop_times.txt not found — skipping"))

        self.stdout.write(self.style.SUCCESS("GTFS import finished ✅"))
