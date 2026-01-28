# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""WireGuard module provides programmable interface for managing WireGuard network interfaces."""

import collections
import configparser
import io
import pathlib
import shutil
import subprocess
import time

from charmlibs import apt, systemd

import wgdb

_WG_QUICK_CONFIG_DIR = pathlib.Path("/etc/wireguard/")

WireguardKeypair = collections.namedtuple("WireguardKeypair", ["private_key", "public_key"])


def generate_public_key(private_key: str) -> str:
    """Generate public key from private key.

    Args:
        private_key: The private key.

    Returns:
        The generated public key.
    """
    return subprocess.check_output(["wg", "pubkey"], input=private_key, encoding="ascii").strip()  # noqa: S607


def generate_keypair() -> WireguardKeypair:
    """Generate a WireGuard private key.

    Returns:
        The generated keypair.
    """
    private_key = subprocess.check_output(["wg", "genkey"], encoding="ascii").strip()  # noqa: S607
    public_key = generate_public_key(private_key)
    return WireguardKeypair(private_key, public_key)


def _wg_config(interface: wgdb.WireguardLink, is_provider: bool, quick: bool) -> str:
    """Generate wg configuration.

    Args:
        interface: The WireGuard interface configuration.
        is_provider: Whether this unit is the provider.
        quick: Whether this configuration is for wg-quick.

    Returns:
        The generated configuration string.
    """
    interface_config = {"ListenPort": interface.port, "PrivateKey": interface.private_key}
    peer_config = {
        "PublicKey": interface.peer_public_key,
        "AllowedIPs": (
            "224.0.0.0/24, ff02::/16, 169.254.0.0/24, fe80::0/64"
            + ("," if interface.peer_allowed_ips else "")
            + ", ".join(map(str, interface.peer_allowed_ips))
        ),
        "Endpoint": interface.peer_endpoint,
        "PersistentKeepalive": 5,
    }
    if quick:
        interface_config["Address"] = (
            "169.254.0.1/24, fe80::1/64" if is_provider else "169.254.0.2/24, fe80::2/64"
        )
        interface_config["Table"] = "off"
    config = configparser.ConfigParser()
    config.optionxform = str  # type: ignore
    config["Interface"] = interface_config
    config["Peer"] = peer_config
    buffer = io.StringIO()
    config.write(buffer)
    return buffer.getvalue()


def _wg_showconf(name: str) -> wgdb.WireguardLink:
    """Show WireGuard configuration for an interface.

    Args:
        name: The name of the WireGuard interface (e.g., 'wg0').

    Returns:
        The WireGuard interface configuration.
    """
    conf_str = subprocess.check_output(["wg", "showconf", name], encoding="ascii")  # noqa: S607
    config = configparser.ConfigParser()
    config.read_string(conf_str)
    private_key = config.get("Interface", "PrivateKey")
    # The showconf command does not display the public key.
    # Derive the public key from the private key instead ,the public key is deterministically
    # derived.
    public_key = generate_public_key(private_key)
    return wgdb.WireguardLink.model_validate(
        {
            "owner": 0,
            "status": wgdb.WireguardLinkStatus.OPEN,
            "public_key": public_key,
            "private_key": private_key,
            "port": int(config.get("Interface", "ListenPort")),
            "peer_public_key": config.get("Peer", "PublicKey"),
            "peer_endpoint": config.get("Peer", "Endpoint"),
            "peer_allowed_ips": config.get("Peer", "AllowedIPs").split(","),
        }
    )


def _wg_config_equal(left: wgdb.WireguardLink, right: wgdb.WireguardLink) -> bool:
    """Return whether two WireGuard configurations are effectively identical.

    This function compares only the parts of wgdb.WireguardLink that would be
    materialized on the WireGuard interface. It ignores fields that do not affect
    the interface state (for example: status, owner, etc.).

    Args:
        left: The left-hand operand.
        right: The right-hand operand.

    Returns:
        True if both configurations would result in the same WireGuard interface.
    """
    return (
        left.port == right.port
        and left.public_key == right.public_key
        and left.peer_public_key == right.peer_public_key
        and left.peer_endpoint == right.peer_endpoint
        and left.peer_allowed_ips == right.peer_allowed_ips
    )


def wireguard_install() -> None:
    """Install WireGuard package."""
    if not shutil.which("wg-quick"):
        apt.update()
        apt.add_package("wireguard")


def wireguard_list() -> list[wgdb.WireguardLink]:
    """List all WireGuard interfaces.

    Returns:
        A list of WireGuard interface configurations.
    """
    interfaces = [
        i.strip()
        for i in subprocess.check_output(["wg", "show", "interfaces"], encoding="ascii").split()  # noqa: S607
    ]
    return [_wg_showconf(i) for i in interfaces]


def wireguard_add(interface: wgdb.WireguardLink, is_provider: bool) -> None:
    """Add a new WireGuard interface.

    Args:
        interface: The WireGuard interface to add.
        is_provider: Whether this unit is the provider.
    """
    wg_quick_config = _WG_QUICK_CONFIG_DIR / f"{interface.interface_name}.conf"
    wg_quick_config.touch(mode=0o600)
    wg_quick_config.write_text(_wg_config(interface, is_provider=is_provider, quick=True))
    service_name = f"wg-quick@{interface.interface_name}"
    systemd.service_enable(service_name)
    systemd.service_start(service_name)
    deadline = time.time() + 60
    while time.time() < deadline:
        if systemd.service_running(service_name):
            return
    raise RuntimeError(f"failed to start {service_name} service")


def wireguard_remove(interface: wgdb.WireguardLink) -> None:
    """Remove a WireGuard interface.

    Args:
        interface: The WireGuard interface to remove.
    """
    service_name = f"wg-quick@{interface.interface_name}"
    systemd.service_stop(service_name)
    systemd.service_disable(service_name)
    wg_quick_config = _WG_QUICK_CONFIG_DIR / f"{interface.interface_name}.conf"
    wg_quick_config.unlink(missing_ok=True)


def wireguard_syncconf(interface: wgdb.WireguardLink, is_provider: bool) -> None:
    """Apply WireGuard configuration to WireGuard interface.

    Args:
        interface: The WireGuard interface to sync.
        is_provider: Whether this unit is on the provider of the relation.
    """
    subprocess.check_output(
        ["wg", "syncconf", interface.interface_name, "/dev/stdin"],  # noqa: S607
        input=_wg_config(interface, is_provider=is_provider, quick=False).encode("ascii"),
    )
    wg_quick_config = _WG_QUICK_CONFIG_DIR / f"{interface.interface_name}.conf"
    wg_quick_config.touch(mode=0o600)
    wg_quick_config.write_text(_wg_config(interface, is_provider=is_provider, quick=True))


def wireguard_apply_db(db: wgdb.WireguardDb, provider_map: dict[int, bool]) -> None:
    """Sync WireGuard interfaces with database.

    Args:
        db: The WireGuard database.
        provider_map: Mapping of relation ID to provider status.
    """
    interfaces = {w.port: w for w in wireguard_list()}
    for link in db.list_link(include_half_closed=True):
        if link.status == wgdb.WireguardLinkStatus.HALF_OPEN:
            continue
        if link.port in interfaces:
            if not _wg_config_equal(link, interfaces[link.port]):
                wireguard_syncconf(link, is_provider=provider_map[link.owner])
            del interfaces[link.port]
        else:
            wireguard_add(link, is_provider=provider_map[link.owner])
    for interface in interfaces.values():
        wireguard_remove(interface)
