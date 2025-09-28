import csv


def remove_columns(input_file, output_file):
    # columns to remove (0-indexed)
    cols_to_remove = {1, 3, 6, 7}

    with open(input_file, "r", newline="", encoding="utf-8") as infile, open(
        output_file, "w", newline="", encoding="utf-8"
    ) as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            # Keep only columns not in cols_to_remove
            new_row = [val for idx, val in enumerate(row) if idx not in cols_to_remove]
            writer.writerow(new_row)


if __name__ == "__main__":
    remove_columns("stops2.txt", "output.csv")
