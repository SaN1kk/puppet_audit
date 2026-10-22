#!/usr/bin/env python3
"""Export one PuppetDB node to a single CSV row."""

import argparse
import csv
import json
import os
import shlex
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import (
    HTTPBasicAuthHandler, HTTPPasswordMgrWithDefaultRealm, Request, build_opener,
)


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


def load_config():
    """Read simple KEY=value settings; existing environment variables take priority."""
    path = Path(__file__).with_name(".env")
    if path.exists():
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key.strip().isidentifier():
                raise ValueError(f".env:{number}: expected KEY=value")
            parts = shlex.split(value, comments=True)
            if len(parts) > 1:
                raise ValueError(f".env:{number}: enclose values containing spaces in quotes")
            os.environ.setdefault(key.strip(), parts[0] if parts else "")

    url = os.getenv("PUPPET_API", "")
    if not url:
        raise ValueError("Set PUPPET_API in .env or environment variables")
    user, password = os.getenv("PUPPET_USER"), os.getenv("PUPPET_PASSWORD")
    if (user is None) != (password is None):
        raise ValueError("Set both PUPPET_USER and PUPPET_PASSWORD, or neither")
    passwords = HTTPPasswordMgrWithDefaultRealm()
    if user is not None:
        passwords.add_password(None, url, user, password)
    return url, build_opener(HTTPBasicAuthHandler(passwords))


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


def pql(client, url, query):
    request = Request(
        url,
        data=json.dumps({"query": query}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with client.open(request, timeout=30) as response:
            data = json.load(response)
    except HTTPError as error:
        with error:
            detail = " ".join(error.read(2000).decode("utf-8", errors="replace").split())
        raise ValueError(
            f"HTTP {error.code} {error.reason}; URL: {error.url}; "
            f"query: {query}; response: {detail or '(empty)'}"
        ) from None
    if not isinstance(data, list):
        raise ValueError("API response must be a JSON array; check PUPPET_API")
    return data


def collect(client, url, host):
    host = json.dumps(host, ensure_ascii=False)
    inventory = pql(client, url, f"inventory {{ certname = {host} }}")
    if not inventory:
        raise ValueError(f"No active node with facts found: {host}")

    node = inventory[0]
    resources = pql(
        client, url,
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
    try:
        url, client = load_config()
        row = collect(client, url, args.host)
        with open(args.output, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=row)
            writer.writeheader()
            writer.writerow(row)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
