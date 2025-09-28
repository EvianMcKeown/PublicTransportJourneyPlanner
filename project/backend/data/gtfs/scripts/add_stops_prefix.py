import csv


def add_prefix_to_first_column(input_file, output_file, prefix):
    with open(input_file, "r", newline="", encoding="utf-8") as infile, open(
        output_file, "w", newline="", encoding="utf-8"
    ) as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            if row:  # skip empty rows
                row[0] = prefix + row[0]
            writer.writerow(row)


if __name__ == "__main__":
    add_prefix_to_first_column("stops2.txt", "output-prefix.txt", "ga_")
