# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Network related functions."""

import collections
import ipaddress
import json
import subprocess  # nosec


def get_mtu(destination: ipaddress.IPv4Address | ipaddress.IPv6Address) -> int:
    """Get the MTU to a destination IP address.

    The per-route MTU takes precedence over the link MTU. If the route does not
    have an explicit MTU, the MTU of the outgoing network interface is returned.

    Args:
        destination: The destination IPv4 or IPv6 address.

    Return:
        MTU value as an integer.
    """
    route_out = subprocess.check_output(
        ["ip", "-j", "route", "get", str(destination)],  # nosec # noqa: S607
        encoding="utf-8",
    )
    route = json.loads(route_out)[0]
    for metric in route.get("metrics", []):
        if "mtu" in metric:
            return metric["mtu"]
    link_out = subprocess.check_output(
        ["ip", "-j", "link", "show", route["dev"]],  # nosec # noqa: S607
        encoding="utf-8",
    )
    return json.loads(link_out)[0]["mtu"]


def get_router_id() -> str:
    """Get router ID of this machine.

    Return:
        Router ID as string.
    """
    out = subprocess.check_output(["ip", "-4", "-j", "route", "get", "1.2.3.4"], encoding="utf-8")  # nosec # noqa: S607
    return json.loads(out)[0]["prefsrc"]


def _get_network_interface(ip: ipaddress.IPv4Interface | ipaddress.IPv6Interface) -> str | None:
    """Get network interface associated with the given IP.

    First checks if any interface on the host has an exact matching address.
    If not, falls back to route-based lookup.

    Return:
        Network interface name, or None if no match or route was found.
    """
    addr_out = subprocess.check_output(
        ["ip", f"-{ip.version}", "-j", "addr", "show"],  # nosec # noqa: S607
        encoding="utf-8",
    )
    for interface in json.loads(addr_out):
        for addr_info in interface.get("addr_info", []):
            if addr_info.get("local") == str(ip.ip):
                return interface["ifname"]
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
    interfaces: list[str] = [name for name in map(_get_network_interface, ips) if name]
    names.update(interfaces)
    name = (
        names.most_common(1)[0][0]
        if names
        # fallback to the default route if none are found for VIPs
        else _get_network_interface(ipaddress.IPv4Interface("1.2.3.4/32"))
    )
    if not name:
        raise RuntimeError("unable to get network interface")
    return name
