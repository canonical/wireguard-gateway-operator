# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Network related functions."""

import collections
import ipaddress
import json
import subprocess  # nosec


def get_router_id() -> str:
    """Get router ID of this machine.

    Return:
        Router ID as string.
    """
    out = subprocess.check_output(["ip", "-4", "-j", "route", "get", "1.2.3.4"], encoding="utf-8")  # nosec # noqa: S607
    return json.loads(out)[0]["prefsrc"]


def _get_network_interface(ip: ipaddress.IPv4Interface | ipaddress.IPv6Interface) -> str | None:
    """Get network interface associated with the give IP.

    Return:
        Network interface name, or None if no route was found.
    """
    try:
        out = subprocess.check_output(
            ["ip", f"-{ip.version}", "-j", "route", "get", str(ip.ip)],  # nosec # noqa: S607
            encoding="utf-8",
        )
        return json.loads(out)[0]["dev"]
    except subprocess.CalledProcessError:
        return None


def get_network_interface(ips: list[ipaddress.IPv4Interface | ipaddress.IPv6Interface]) -> str:
    """Get network interface associated with the given IPs.

    Return:
        Network interface name.
    """
    names: collections.Counter[str] = collections.Counter()
    interfaces: list[str] = [n for n in map(_get_network_interface, ips) if n]
    names.update(interfaces)
    if not names:
        name = _get_network_interface(ipaddress.IPv4Interface("1.2.3.4/32"))
        if not name:
            raise RuntimeError("unable to get network interface")
        return name
    return names.most_common(1)[0][0]
