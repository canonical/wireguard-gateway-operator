# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Network related functions."""

import json
import subprocess  # nosec


def get_router_id() -> str:
    """Get router ID of this machine.

    Return:
        Router ID as string.
    """
    out = subprocess.check_output(["ip", "-4", "-j", "route", "get", "1.2.3.4"], encoding="utf-8")  # noqa: S607 # nosec
    return json.loads(out)[0]["prefsrc"]


def get_network_interface() -> str:
    """Get main network interface.

    Return:
        Network interface name.
    """
    out = subprocess.check_output(["ip", "-4", "-j", "route", "get", "1.2.3.4"], encoding="utf-8")  # noqa: S607 # nosec
    return json.loads(out)[0]["dev"]
