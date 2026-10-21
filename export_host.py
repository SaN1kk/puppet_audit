#!/usr/bin/env python3
"""Export one PuppetDB node to a single CSV row."""

import argparse
import csv
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# CSV column -> path in the structured facts.
FACTS = {
    "hostname": "networking.hostname",
    "fqdn": "networking.fqdn",
    "os": "os.name",
    "os_version": "os.release.full",
    "architecture": "os.architecture",
    "kernel": "kernel",
    "kernel_release": "kernelrelease",
    "uptime": "system_uptime.uptime",
    "load_average": "load_averages",
    "manufacturer": "dmi.manufacturer",
    "model": "dmi.product.name",
    "serial": "dmi.product.serial_number",
    "uuid": "dmi.product.uuid",
    "bios_version": "dmi.bios.version",
    "bios_date": "dmi.bios.release_date",
    "board": "dmi.board.product",
    "board_serial": "dmi.board.serial_number",
    "cpu_physical": "processors.physicalcount",
    "cpu_logical": "processors.count",
    "cpu_models": "processors.models",
    "ram_total": "memory.system.total",
    "ram_available": "memory.system.available",
    "disks": "disks",
    "partitions": "partitions",
    "filesystems": "mountpoints",
    "primary_interface": "networking.primary",
    "primary_ip": "networking.ip",
    "primary_mac": "networking.mac",
    "interfaces": "networking.interfaces",
}
SERVICES = ("kesl", "telegraf", "zabbix-agent", "zabbix-agent2", "auditd")


def get(data, path):
    for key in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def cell(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else value


def pql(session, url, query):
    response = session.post(url, json={"query": query}, timeout=(10, 30))
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("API response must be a JSON array; check PUPPET_API")
    return data


def collect(session, url, host):
    host = json.dumps(host, ensure_ascii=False)
    inventory = pql(session, url, f"inventory {{ certname = {host} }}")
    if not inventory:
        raise ValueError(f"No active node with facts found: {host}")

    node = inventory[0]
    resources = pql(
        session, url,
        f'resources[title, parameters] {{ certname = {host} '
        f'and type = "Service" }}',
    )
    services = {item["title"]: item.get("parameters") for item in resources}
    row = {
        "certname": node["certname"],
        "environment": node.get("environment"),
        "facts_timestamp": node.get("timestamp"),
    }
    row.update({column: get(node["facts"], path) for column, path in FACTS.items()})
    row.update({name.replace("-", "_"): services.get(name) for name in SERVICES})
    return {column: cell(value) for column, value in row.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Exact Puppet certname")
    parser.add_argument("-o", "--output", default="host.csv")
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"), encoding="utf-8-sig")
    url = os.getenv("PUPPET_API")
    if not url:
        parser.error("Set PUPPET_API in .env or environment variables")
    user, password = os.getenv("PUPPET_USER"), os.getenv("PUPPET_PASSWORD")
    if (user is None) != (password is None):
        parser.error("Set both PUPPET_USER and PUPPET_PASSWORD, or neither")

    try:
        with requests.Session() as session:
            if user is not None:
                session.auth = (user, password)
            row = collect(session, url.rstrip("/"), args.host)
        with open(args.output, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=row)
            writer.writeheader()
            writer.writerow(row)
    except (requests.RequestException, ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
