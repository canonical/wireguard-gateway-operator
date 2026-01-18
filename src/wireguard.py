# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""WireGuard module provides programmable interface for managing WireGuard network interfaces."""

import collections
import configparser
import pathlib
import shutil
import subprocess
import textwrap

from charmlibs import apt
from charmlibs import systemd

import wgdb

_WG_QUICK_CONFIG_DIR = pathlib.Path("/etc/wireguard/")

WireguardKeypair = collections.namedtuple(
    "WireguardKeyPair", ["private_key", "public_key"]
)


def generate_keypair() -> WireguardKeypair:
    """Generate a WireGuard private key.

    Returns:
        The generated keypair.
    """
    private_key = subprocess.check_output(["wg", "genkey"], encoding="ascii").strip()
    public_key = subprocess.check_output(
        ["wg", "pubkey"], input=private_key, encoding="ascii"
    ).strip()
    return WireguardKeypair(private_key, public_key)


def _wg_quick_config(interface: wgdb.WireguardLink, is_provider: bool) -> str:
    """Generate wg-quick configuration.

    Args:
        interface: The WireGuard interface configuration.
        is_provider: Whether this unit is the provider.

    Returns:
        The generated configuration string.
    """
    if is_provider:
        address = "169.254.0.1/24, fe80::1/64"
    else:
        address = "169.254.0.2/24, fe80::2/64"
    config = textwrap.dedent(
        f"""\
        [Interface]
        Address = {address}
        PrivateKey = {interface.private_key}
        Table = off
        
        [Peer]
        PublicKey = {interface.peer_public_key}
        AllowedIPs = {", ".join(map(str,interface.allowed_ips))}
        Endpoint = {interface.peer_endpoint}
        PersistentKeepalive = 5
        """
    )
    return config


def _wg_config(interface: wgdb.WireguardLink) -> str:
    """Generate wg configuration.

    Args:
        interface: The WireGuard interface configuration.

    Returns:
        The generated configuration string.
    """
    return textwrap.dedent(
        f"""\
        [Interface]
        PrivateKey = {interface.private_key}
    
        [Peer]
        PublicKey = {interface.peer_public_key}
        AllowedIPs = 224.0.0.0/24, ff02::/16, 169.254.0.0/24, fe80::0/64, {", ".join(map(str,interface.allowed_ips))}
        Endpoint = {interface.peer_endpoint}
        PersistentKeepalive = 5
        """
    )


def _wg_showconf(name: str) -> wgdb.WireguardLink:
    """Show WireGuard configuration for an interface.

    Args:
        name: The name of the WireGuard interface (e.g., 'wg0').

    Returns:
        The WireGuard interface configuration.
    """
    conf_str = subprocess.check_output(["wg", "showconf", name], encoding="ascii")
    config = configparser.ConfigParser()
    config.read_string(conf_str)
    private_key = config.get("Interface", "PrivateKey")
    public_key = generate_public_key(private_key)
    return wgdb.WireguardLink.model_validate(
        dict(
            status=wgdb.WireguardLinkStatus.OPEN,
            public_key=public_key,
            private_key=private_key,
            port=int(config.get("Interface", "ListenPort")),
            peer_public_key=config.get("Peer", "PublicKey"),
            peer_endpoint=config.get("Peer", "Endpoint"),
            peer_allowed_ips=config.get("Peer", "AllowedIPs").split(","),
        )
    )


def wireguard_install() -> None:
    """Install WireGuard package."""
    if not shutil.which("wg-quick"):
        apt.add_package("wireguard", "wireguard-tools")


def wireguard_list() -> list[wgdb.WireguardLink]:
    """List all WireGuard interfaces.

    Returns:
        A list of WireGuard interface configurations.
    """
    interfaces = [
        i.strip()
        for i in subprocess.check_output(
            ["wg", "show", "interfaces"], encoding="ascii"
        ).split()
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
    wg_quick_config.write_text(_wg_quick_config(interface, is_provider))
    service_name = f"wg-quick@{interface.interface_name}"
    systemd.service_enable(service_name)
    systemd.service_start(service_name)


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


def wireguard_syncconf(interface: wgdb.WireguardLink) -> None:
    """Sync WireGuard configuration.

    Args:
        interface: The WireGuard interface to sync.
    """
    name = f"wg{interface.port}"
    subprocess.check_output(
        ["wg", "syncconf", name, "/dev/stdin"],
        input=_wg_config(interface).encode("ascii"),
    )
