import csv
import os
import re


def fix_stop_ids():
    """
    Corrects the stop_id column in stop_times.csv for trips associated
    with 'mycity' routes.

    It identifies 'mycity' routes from trips.csv, gets the associated trip_ids,
    creates a mapping of stop_name to stop_id from stops.csv, and then
    iterates through stop_times.csv to replace the incorrect stop_names with
    the correct stop_ids.
    """
    # Define file paths
    stops_file = "stops.txt"
    trips_file = "trips.txt"
    stop_times_file = "stop_times.txt"
    output_file = "stop_times_corrected.txt"

    print("Starting the correction process...")

    # Helper function to normalize strings
    def normalize_string(s):
        """Converts string to lowercase and removes punctuation."""
        s = s.lower()
        s = re.sub(
            r"[^\w\s]", "", s
        )  # Remove punctuation except letters, numbers, and whitespace
        return s.strip()

    # 1. Create a mapping from normalized stop_name to stop_id
    stop_name_to_id = {}
    try:
        with open(stops_file, mode="r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                normalized_stop_name = normalize_string(row["stop_name"])
                stop_name_to_id[normalized_stop_name] = row["stop_id"]
        print(
            f"Successfully created a map for {len(stop_name_to_id)} stops from {stops_file}."
        )
    except FileNotFoundError:
        print(f"Error: {stops_file} not found.")
        return

    # 2. Identify trip_ids for 'mycity' routes
    mycity_trip_ids = set()
    try:
        with open(trips_file, mode="r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row["route_id"].startswith("mc_"):
                    mycity_trip_ids.add(row["trip_id"])
        print(
            f"Found {len(mycity_trip_ids)} trips for 'mycity' routes in {trips_file}."
        )
    except FileNotFoundError:
        print(f"Error: {trips_file} not found.")
        return

    # 3. Read stop_times.csv, correct the rows, and write to a new file
    corrected_rows = []
    try:
        with open(stop_times_file, mode="r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            headers = reader.fieldnames
            corrected_rows.append(headers)  # Add header to our list

            for row in reader:
                # Check if this row's trip_id needs to be fixed
                if row["trip_id"] in mycity_trip_ids:
                    stop_name_from_stop_times = row[
                        "stop_id"
                    ]  # This is actually the stop_name

                    # Normalize the stop_name from stop_times.txt for lookup
                    normalized_stop_name = normalize_string(stop_name_from_stop_times)

                    # Look up the correct stop_id using the normalized name
                    correct_stop_id = stop_name_to_id.get(normalized_stop_name)

                    if correct_stop_id:
                        row["stop_id"] = correct_stop_id
                    else:
                        print(
                            f"Warning: Could not find a matching stop_id for normalized stop_name '{normalized_stop_name}' (original: '{stop_name_from_stop_times}')"
                        )

                # Convert row dict back to a list in the correct order
                corrected_rows.append([row[h] for h in headers])

        print(f"Processed {len(corrected_rows) - 1} records from {stop_times_file}.")

    except FileNotFoundError:
        print(f"Error: {stop_times_file} not found.")
        return

    # 4. Write the corrected data to the output file
    try:
        with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            writer.writerows(corrected_rows)
        print(f"Successfully wrote corrected data to {output_file}.")
        # Optional: uncomment the lines below to replace the original file
        # os.remove(stop_times_file)
        # os.rename(output_file, stop_times_file)
        # print(f"Original {stop_times_file} has been replaced with the corrected version.")

    except IOError as e:
        print(f"Error writing to file: {e}")


if __name__ == "__main__":
    fix_stop_ids()
