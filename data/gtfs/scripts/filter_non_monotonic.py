import csv

txt_file = "non_monotone_trips.txt"
csv_file = "trips.txt"
output_file = "trips_filtered.csv"  # safer than overwriting directly

# Step 1: read trip_ids from txt file
with open(txt_file, "r") as f:
    trip_ids_to_remove = {line.split()[0] for line in f if line.strip()}

print(f"Found {len(trip_ids_to_remove)} trip_ids to remove.")

# Step 2: read trips.csv and filter
with open(csv_file, newline="", encoding="utf-8") as infile, open(
    output_file, "w", newline="", encoding="utf-8"
) as outfile:

    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()

    removed_count = 0
    kept_count = 0

    for row in reader:
        if row["trip_id"] in trip_ids_to_remove:
            removed_count += 1
        else:
            writer.writerow(row)
            kept_count += 1

print(f"Removed {removed_count} rows, kept {kept_count} rows.")
print(f"Filtered CSV written to {output_file}")
