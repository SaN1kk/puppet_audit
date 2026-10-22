#!/usr/bin/env python3
"""Export PuppetDB nodes listed in a text file to one CSV table."""

import argparse
import csv
import sys
from pathlib import Path

from export_host import FACTS, SERVICES, collect, load_config


def read_hosts(filename):
    lines = Path(filename).read_text(encoding="utf-8-sig").splitlines()
    hosts = [
        line.strip() for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return list(dict.fromkeys(hosts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hosts_file", help="UTF-8 file: one exact Puppet certname per line")
    parser.add_argument("-o", "--output", default="hosts.csv")
    args = parser.parse_args()
    if Path(args.hosts_file).resolve() == Path(args.output).resolve():
        parser.error("Input and output must be different files")

    columns = ["certname", "environment", "facts_timestamp", *FACTS]
    columns.extend(name.replace("-", "_") for name in SERVICES)
    columns.append("error")
    failed = 0
    try:
        url, client = load_config()
        hosts = read_hosts(args.hosts_file)
        if not hosts:
            parser.error("Host list is empty")
        with open(args.output, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for host in hosts:
                try:
                    row = collect(client, url, host)
                except (OSError, ValueError) as error:
                    failed += 1
                    row = {"certname": host, "error": str(error)}
                    print(f"{host}: {error}", file=sys.stderr)
                writer.writerow(row)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Saved: {args.output} | OK: {len(hosts) - failed} | Errors: {failed}")
    if failed:
        parser.exit(1)


if __name__ == "__main__":
    main()
