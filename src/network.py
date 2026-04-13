# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Network related functions."""

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


def get_network_interface() -> str:
    """Get main network interface.

    Return:
        Network interface name.
    """
    out = subprocess.check_output(["ip", "-4", "-j", "route", "get", "1.2.3.4"], encoding="utf-8")  # nosec # noqa: S607
    return json.loads(out)[0]["dev"]
