import csv

# Read all stop_ids that are actually used in stop_times.txt
valid_stop_ids = set()
with open("stop_times.txt", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        valid_stop_ids.add(row["stop_id"])

# Filter stops.txt
with open("stops.txt", newline="", encoding="utf-8") as f_in, open(
    "stops_filtered.txt", "w", newline="", encoding="utf-8"
) as f_out:

    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)

    writer.writeheader()
    for row in reader:
        if row["stop_id"] in valid_stop_ids:
            writer.writerow(row)

print("Filtered stops written to stops_filtered.txt")
