# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit test helpers."""

import charm
import wgdb


def example_public_key(name: str, n: int) -> str:
    """Generate a fake public key for testing.

    Args:
        name: Name to include in the key.
        n: Number to include in the key.

    Returns:
        Fake public key string.
    """
    padding = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    key = f"public/key/{name}/{n}/"
    return key + padding[len(key) :]


def example_private_key(name: str, n: int) -> str:
    """Generate a fake private key for testing.

    Args:
        name: Name to include in the key.
        n: Number to include in the key.

    Returns:
        Fake private key string.
    """
    padding = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    key = f"private/key/{name}/{n}/"
    return key + padding[len(key) :]

def get_wgdb() -> wgdb.WireguardDb:
    """Get the WireguardDb instance used in tests.

    Returns:
        The WireguardDb instance.
    """
    return wgdb.WireguardDb(file=charm._WGDB_DIR / "wireguard-gateway-0.json")