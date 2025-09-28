import csv


def remove_prefix_from_first_column(input_file, output_file, prefix):
    with open(input_file, "r", newline="", encoding="utf-8") as infile, open(
        output_file, "w", newline="", encoding="utf-8"
    ) as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            if row:  # skip empty rows
                if row[0].startswith(prefix):
                    writer.writerow(row[0][len(prefix) :])  # write header as is


if __name__ == "__main__":
    remove_prefix_from_first_column(
        "routes2.txt", "output-routes-prefix-removed.txt", "ga_"
    )
