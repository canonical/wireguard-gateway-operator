# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Bird module provides programmable interface for managing BIRD internet routing daemon."""

import ipaddress
import pathlib
import shutil
import subprocess  # nosec
import textwrap

import jinja2
from charmlibs import apt

import network
import wgdb

_BIRD_CONF_TEMPLATE = pathlib.Path(__file__).parent.parent / "templates/bird.conf.j2"
_BIRD_CONF_FILE = pathlib.Path("/etc/bird/bird.conf")
_SYSCTL_FILE = pathlib.Path("/etc/sysctl.d/99-wireguard-gateway.conf")


def bird_install() -> None:
    """Install BIRD using apt if not installed."""
    if not shutil.which("birdc"):
        apt.update()
        apt.add_package("bird2")
    if not _SYSCTL_FILE.exists():
        _SYSCTL_FILE.touch()
        _SYSCTL_FILE.write_text(
            textwrap.dedent(
                """\
                net.ipv4.ip_forward = 1
                net.ipv6.conf.all.forwarding = 1
                """
            )
        )
        subprocess.check_call(["sysctl", "--system"])  # nosec # noqa: S607


def bird_config(
    router_id: str,
    interfaces: list[wgdb.WireguardLink],
    advertise_prefixes: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> str:
    """Generate BIRD configuration.

    Args:
        router_id: router id.
        interfaces: WireGuard interfaces.
        advertise_prefixes: Advertise prefixes.

    Return:
        BIRD configuration content.
    """
    template = _BIRD_CONF_TEMPLATE.read_text()
    ipv4_prefixes = [
        str(prefix) for prefix in advertise_prefixes if isinstance(prefix, ipaddress.IPv4Network)
    ]
    ipv6_prefixes = [
        str(prefix) for prefix in advertise_prefixes if isinstance(prefix, ipaddress.IPv6Network)
    ]
    return (
        jinja2.Environment(loader=jinja2.BaseLoader(), autoescape=True)
        .from_string(template)
        .render(
            router_id=router_id,
            interfaces=interfaces,
            ipv4_prefixes=ipv4_prefixes,
            ipv6_prefixes=ipv6_prefixes,
        )
    )


def bird_reload(config: str) -> None:
    """Reload BIRD configuration if configuration changed.

    Args:
        config: BIRD configuration content.
    """
    if _BIRD_CONF_FILE.read_text(encoding="utf-8") != config:
        _BIRD_CONF_FILE.write_text(config, encoding="utf-8")
        subprocess.check_call(["birdc", "configure"])  # nosec # noqa: S607


def bird_apply_db(
    db: wgdb.WireguardDb,
    advertise_prefixes: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> None:
    """Sync BIRD configuration with WireGuard database.

    Args:
        db: WireGuard database.
        advertise_prefixes: List of prefixes to advertise.
    """
    config = bird_config(
        router_id=network.get_router_id(),
        interfaces=db.list_link(),
        advertise_prefixes=advertise_prefixes,
    )
    bird_reload(config)
