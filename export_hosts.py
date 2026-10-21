#!/usr/bin/env python3
"""Export PuppetDB nodes listed in a text file to one CSV table."""

import argparse
import csv
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from export_host import FACTS, SERVICES, collect


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
    load_dotenv(Path(__file__).with_name(".env"), encoding="utf-8-sig")
    url = os.getenv("PUPPET_API")
    if not url:
        parser.error("Set PUPPET_API in .env or environment variables")
    user, password = os.getenv("PUPPET_USER"), os.getenv("PUPPET_PASSWORD")
    if (user is None) != (password is None):
        parser.error("Set both PUPPET_USER and PUPPET_PASSWORD, or neither")
    if Path(args.hosts_file).resolve() == Path(args.output).resolve():
        parser.error("Input and output must be different files")

    columns = ["certname", "environment", "facts_timestamp", *FACTS]
    columns.extend(name.replace("-", "_") for name in SERVICES)
    columns.append("error")
    failed = 0
    try:
        hosts = read_hosts(args.hosts_file)
        if not hosts:
            parser.error("Host list is empty")
        with requests.Session() as session, open(
            args.output, "w", newline="", encoding="utf-8-sig"
        ) as file:
            if user is not None:
                session.auth = (user, password)
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for host in hosts:
                try:
                    row = collect(session, url.rstrip("/"), host)
                except (requests.RequestException, ValueError) as error:
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
