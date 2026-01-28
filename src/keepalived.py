# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Keepalived module provides programmable interface for managing keepalived instances."""

import ipaddress
import pathlib
import shutil

import jinja2
from charmlibs import apt, systemd

import network

_KEEPALIVED_CONF_TEMPLATE = pathlib.Path(__file__).parent.parent / "templates/keepalived.conf.j2"
_KEEPALIVED_CONF_FILE = pathlib.Path("/etc/keepalived/keepalived.conf")
_CHECK_ROUTER_SCRIPT = pathlib.Path(__file__).parent.parent / "scripts/check_route"


def keepalived_install():
    """Install keepalived."""
    if not shutil.which("keepalived"):
        apt.update()
        apt.add_package("keepalived")


def _keepalived_render_config(
    vips: list[ipaddress.IPv4Interface | ipaddress.IPv6Interface],
    check_routes: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> str:
    """Generate a keepalived configuration.

    Args:
        vips: A list of virtual IP addresses (VIPs) managed by keepalived.
        check_routes: A list of route destinations used to verify connectivity, route reachability
            is used to decide when VIP failover should occur.

    Returns:
        Keepalived configuration content.
    """
    template = _KEEPALIVED_CONF_TEMPLATE.read_text()
    return (
        jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        .from_string(template)
        .render(
            router_id=network.get_router_id(),
            interface=network.get_network_interface(),
            vips=vips,
            check_routes=check_routes,
            check_route_script=_CHECK_ROUTER_SCRIPT.absolute(),
        )
    )


def keepalived_reload(
    vips: list[ipaddress.IPv4Interface | ipaddress.IPv6Interface],
    check_routes: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> None:
    """Reload keepalived configuration.

    Args:
        vips: A list of virtual IP addresses (VIPs) managed by keepalived.
        check_routes: A list of route destinations used to verify connectivity, route reachability
            is used to decide when VIP failover should occur.
    """
    current = (
        _KEEPALIVED_CONF_FILE.read_text(encoding="utf-8") if _KEEPALIVED_CONF_FILE.exists() else ""
    )
    config = _keepalived_render_config(vips, check_routes)
    changed = current != config
    if changed:
        _KEEPALIVED_CONF_FILE.write_text(config)
    if systemd.service_running("keepalived"):
        if changed:
            systemd.service_reload("keepalived")
    else:
        systemd.service_start("keepalived")


def keepalived_stop():
    """Stop keepalived service."""
    systemd.service_stop("keepalived")
